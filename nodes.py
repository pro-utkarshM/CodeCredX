# nodes.py
from pocketflow import Node
import re
import requests
import base64
import logging
import random
import io
from typing import List, Dict, Any, Optional

import PyPDF2 # Ensure this is installed: pip install PyPDF2

from utils.call_llm import call_llm
from config import app_config

logger = logging.getLogger(__name__)

class ResumeInputNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Optional[str]:
        """
        Retrieves the resume file path from the shared dictionary.
        This path will be passed as an argument to the exec method.
        """
        file_path = shared.get("resume_file_path")
        if file_path:
            logger.debug(f"Resume file path retrieved from shared in prep: {file_path}")
        return file_path

    def exec(self, file_path: Optional[str]) -> str:
        """
        Reads resume content from the provided file_path or falls back to simulated content.
        Supports .txt and .pdf file reading.
        """
        resume_content = ""
        if file_path:
            logger.info(f"Attempting to read resume content from file: {file_path}")
            try:
                if file_path.lower().endswith('.pdf'):
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page_num in range(len(reader.pages)):
                            page = reader.pages[page_num]
                            resume_content += page.extract_text() or ''
                    logger.info(f"Successfully extracted text from PDF: {file_path}. Content length: {len(resume_content)} chars.")
                elif file_path.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        resume_content = f.read()
                    logger.info(f"Successfully read content from TXT: {file_path}. Content length: {len(resume_content)} chars.")
                else:
                    logger.warning(f"Unsupported file type: {file_path}. Only .txt and .pdf are supported for direct reading. Falling back to simulated content.")
                    file_path = None # Force fallback to simulated content if type is unsupported
            except FileNotFoundError:
                logger.error(f"Resume file not found at: {file_path}. Falling back to simulated content.")
                file_path = None
            except PyPDF2.errors.PdfReadError:
                logger.error(f"Error reading PDF file {file_path}. It might be corrupted or encrypted. Falling back to simulated content.", exc_info=True)
                file_path = None
            except Exception as e:
                logger.error(f"An unexpected error occurred while reading or parsing resume file {file_path}: {e}. Falling back to simulated content.", exc_info=True)
                file_path = None

        if not file_path or not resume_content: # Fallback if file_path was None or reading failed
            logger.info("Using simulated resume content.")
            sample_resume_text = """
            John Doe
            Software Engineer
            Email: john.doe@example.com
            LinkedIn: https://www.linkedin.com/in/johndoe

            Projects:
            - My Awesome Project (Public): https://github.com/octocat/Spoon-Knife
              A cool project demonstrating advanced algorithms.
            - Web Portfolio: https://johndoe.dev
              My personal website showcasing various web development projects.
            - Open Source Contribution (Non-existent Org): https://github.com/org/some-library
              Contributed to an open-source library. (Designed to simulate a 'Repository not found' or similar failure)
            - Another Project (Private/Inaccessible): https://github.com/johndoe/private-repo
              This should not be publicly accessible via unauthenticated requests. (Tests 403/404)
            - Blog Post: https://medium.com/@johndoe/my-tech-blog-post
            - Non-existent User/Repo: https://github.com/nonexistentuser/nonexistentrepo12345
              (Tests 'Repository not found' for bad path)
            - Official OpenAI Python Library (Public): https://github.com/openai/openai-python
            """
            resume_content = sample_resume_text

        return resume_content

    def post(self, shared: Dict[str, Any], prep_res: Optional[str], exec_res: str) -> str:
        """
        Stores the resume text in the shared store.
        """
        shared["resume_text"] = exec_res
        logger.info("Resume text stored in shared.")
        return "default"

class URLExtractionNode(Node):
    def prep(self, shared: Dict[str, Any]) -> str:
        return shared.get("resume_text", "")

    def exec(self, resume_text: str) -> Dict[str, List[str]]:
        """
        Extracts URLs from the provided resume text using more robust regular expressions,
        specifically targeting GitHub, LinkedIn, LeetCode, and general HTTP(S) links.
        It handles variations in text extracted from PDFs like missing protocols or
        trailing punctuation, and filters out non-repository GitHub URLs.
        """
        logger.info("Extracting URLs from resume text...")

        # Normalize whitespace (including newlines) to a single space
        normalized_text = re.sub(r'\s+', ' ', resume_text)

        github_project_urls: List[str] = []
        other_urls: List[str] = []

        # --- Phase 1: Identify and Extract GitHub Project URLs ---
        github_project_pattern = re.compile(
            r'(?:https?://)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)'
            r'(?:[^/\s\(\)]*)?'
            r'(?:\s*\(Source Code\))?',
            re.IGNORECASE
        )

        for match in github_project_pattern.finditer(normalized_text):
            full_match = match.group(0).strip('.,;)!}"\'')
            full_match = re.sub(r'\s*\(Source Code\)\s*', '', full_match, flags=re.IGNORECASE).strip()

            if not full_match.startswith("http"):
                full_match = "https://" + full_match

            base_repo_url_match = re.match(r'(https?://github\.com/[^/]+/[^/]+)', full_match, re.IGNORECASE)
            if base_repo_url_match:
                base_repo_url = base_repo_url_match.group(1)
                if not any(sub in full_match for sub in ["/pull/", "/issues/", "/commit/", "/tree/", "/blob/", "/actions/"]) \
                   and base_repo_url not in github_project_urls:
                    github_project_urls.append(base_repo_url)
                    logger.debug(f"Identified GitHub Project: {base_repo_url}")
            else:
                logger.debug(f"Matched GitHub-like string but not a project URL: {full_match}")

        # --- Phase 2: Identify and Extract other specific profile URLs ---
        linkedin_pattern = re.compile(r'(?:https?://)?linkedin\.com/in/[a-zA-Z0-9_-]+(?:/?(?:[?#].*)?)?', re.IGNORECASE)
        for url in linkedin_pattern.findall(normalized_text):
            clean_url = url.strip('.,;)!}"\'')
            if not clean_url.startswith("http"): clean_url = "https://" + clean_url
            if clean_url not in other_urls: other_urls.append(clean_url)

        leetcode_pattern = re.compile(r'(?:https?://)?leetcode\.com/u/[a-zA-Z0-9_-]+(?:/?(?:[?#].*)?)?', re.IGNORECASE)
        for url in leetcode_pattern.findall(normalized_text):
            clean_url = url.strip('.,;)!}"\'')
            if not clean_url.startswith("http"): clean_url = "https://" + clean_url
            if clean_url not in other_urls: other_urls.append(clean_url)

        # --- Phase 3: Identify General URLs (that haven't been captured yet) ---
        general_url_pattern = re.compile(r'https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s,;)"\']*)?', re.IGNORECASE)
        for url in general_url_pattern.findall(normalized_text):
            clean_url = url.strip('.,;)!}"\'')
            if clean_url not in github_project_urls and clean_url not in other_urls:
                if not clean_url.startswith("http"): clean_url = "https://" + clean_url
                other_urls.append(clean_url)

        extracted_data = {"github_project_urls": github_project_urls, "other_urls": other_urls}
        logger.info(f"Extracted {len(extracted_data['github_project_urls'])} GitHub URLs and {len(extracted_data['other_urls'])} other URLs from resume.")
        return extracted_data

    def post(self, shared: Dict[str, Any], prep_res: str, exec_res: Dict[str, List[str]]) -> str:
        # Store extracted URLs in temporary keys to avoid conflicts before consolidation
        shared["resume_github_urls"] = exec_res["github_project_urls"]
        shared["other_urls"] = exec_res["other_urls"]
        return "default"

class GitHubProfileFetcherNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Optional[str]:
        """Retrieves the GitHub profile URL from the shared dictionary."""
        profile_url = shared.get("github_profile_url")
        if profile_url:
            logger.debug(f"GitHub profile URL retrieved from shared: {profile_url}")
        return profile_url

    def exec(self, profile_url: Optional[str]) -> List[str]:
        """
        Fetches all public repository URLs for a given GitHub profile URL.
        """
        if not profile_url:
            logger.info("No GitHub profile URL provided, skipping profile fetch.")
            return []

        username_match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', profile_url, re.IGNORECASE)
        if not username_match:
            logger.warning(f"Invalid GitHub profile URL format: {profile_url}. Could not extract username.")
            return []
        
        username = username_match.group(1)
        logger.info(f"Fetching public repositories for GitHub user: {username}")

        repos_api_url = f"https://api.github.com/users/{username}/repos"
        headers = {}
        if app_config.GITHUB_TOKEN and app_config.GITHUB_TOKEN != "your-github-personal-access-token-here":
            headers["Authorization"] = f"token {app_config.GITHUB_TOKEN}"

        repo_urls: List[str] = []
        page = 1
        while True:
            try:
                params = {'per_page': 100, 'page': page}
                response = requests.get(repos_api_url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                repos_data = response.json()

                if not repos_data:
                    break

                for repo in repos_data:
                    if not repo.get('fork'):
                        repo_urls.append(repo['html_url'])
                
                logger.info(f"Fetched {len(repos_data)} repos on page {page} for user {username}.")
                if len(repos_data) < 100:
                    break
                page += 1

            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error fetching repos for {username}: {e}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching repos for {username}: {e}")
                break
        
        logger.info(f"Found {len(repo_urls)} non-forked public repositories for user {username}.")
        return repo_urls

    def post(self, shared: Dict[str, Any], prep_res: Optional[str], exec_res: List[str]) -> str:
        """Stores the fetched profile repo URLs in a temporary key."""
        shared["profile_github_urls"] = exec_res
        return "default"

class URLConsolidatorNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Dict[str, List[str]]:
        """Gathers all extracted URL lists from the shared store."""
        return {
            "from_resume": shared.get("resume_github_urls", []),
            "from_profile": shared.get("profile_github_urls", []),
        }

    def exec(self, url_sources: Dict[str, List[str]]) -> List[str]:
        """
        Merges GitHub project URLs from the resume and the user's profile,
        ensuring the final list is unique.
        """
        logger.info("Consolidating GitHub project URLs from all sources...")
        
        from_resume = url_sources.get("from_resume", [])
        from_profile = url_sources.get("from_profile", [])

        consolidated_urls = set(from_resume)
        consolidated_urls.update(from_profile)
        
        final_list = sorted(list(consolidated_urls))
        
        logger.info(f"Consolidated sources: {len(from_resume)} from resume, {len(from_profile)} from profile.")
        logger.info(f"Total unique GitHub project URLs to analyze: {len(final_list)}")
        
        return final_list

    def post(self, shared: Dict[str, Any], prep_res: Dict[str, List[str]], exec_res: List[str]) -> str:
        """Stores the final, unique list of GitHub project URLs in the shared store."""
        shared["github_project_urls"] = exec_res
        return "default"

class GitHubAnalyzerNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[str]:
        return shared.get("github_project_urls", [])

    def exec(self, github_urls: List[str]) -> List[Dict[str, Any]]:
        logger.info("Analyzing GitHub repositories for metadata and READMEs...")
        analyzed_projects: List[Dict[str, Any]] = []
        github_api_base = app_config.GITHUB_API_BASE_URL

        headers = {}
        if app_config.GITHUB_TOKEN and app_config.GITHUB_TOKEN != "your-github-personal-access-token-here":
            headers["Authorization"] = f"token {app_config.GITHUB_TOKEN}"
            logger.info("Using GitHub Personal Access Token for API requests.")
        else:
            logger.warning("GitHub Personal Access Token not provided or is a placeholder. API rate limits and private repo access might be affected.")

        for url in github_urls:
            owner_repo_match = re.match(r'https?://github.com/([^/]+)/([^/]+)', url)
            if not owner_repo_match:
                logger.warning(f"Skipping invalid GitHub URL format encountered: {url}")
                continue

            owner = owner_repo_match.group(1)
            repo_name = owner_repo_match.group(2)
            repo_api_url = f"{github_api_base}{owner}/{repo_name}"

            project_data: Dict[str, Any] = {
                "url": url, "owner": owner, "repo_name": repo_name, "status": "pending",
                "metadata": {}, "readme_content": None, "error": None, "summary": None, "scores": {}
            }

            try:
                repo_response = requests.get(repo_api_url, headers=headers, timeout=10)
                repo_response.raise_for_status()
                repo_metadata = repo_response.json()

                project_data["metadata"] = {
                    "name": repo_metadata.get("name"), "description": repo_metadata.get("description"),
                    "stars": repo_metadata.get("stargazers_count"), "fork": repo_metadata.get("fork"),
                    "topics": repo_metadata.get("topics", []), "visibility": "private" if repo_metadata.get("private") else "public",
                    "created_at": repo_metadata.get("created_at"), "updated_at": repo_metadata.get("updated_at"),
                    "pushed_at": repo_metadata.get("pushed_at"), "size": repo_metadata.get("size")
                }

                readme_api_url = f"{repo_api_url}/contents/README.md"
                readme_response = requests.get(readme_api_url, headers=headers, timeout=10)

                if readme_response.status_code == 200:
                    readme_data = readme_response.json()
                    if readme_data.get("encoding") == "base64" and readme_data.get("content"):
                        project_data["readme_content"] = base64.b64decode(readme_data["content"]).decode('utf-8')
                        logger.info(f"Successfully fetched README for {owner}/{repo_name}.")
                elif readme_response.status_code == 404:
                    project_data["error"] = "README.md not found."
                else:
                    project_data["error"] = f"Failed to fetch README: HTTP Status {readme_response.status_code}."

                project_data["status"] = "success"

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                error_msg = f"HTTP error {status_code}"
                if status_code == 404: error_msg = "Repository not found."
                elif status_code == 403: error_msg = "Access forbidden (private repo or rate limit exceeded)."
                project_data["status"] = "failed"
                project_data["error"] = error_msg
            except requests.exceptions.RequestException as e:
                project_data["status"] = "failed"
                project_data["error"] = f"Network or request error: {e}"
            
            analyzed_projects.append(project_data)
        return analyzed_projects

    def post(self, shared: Dict[str, Any], prep_res: List[str], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        return "default"

# ... (LLMSummarizerNode, ContributionNode, OriginalityNode, TrustHeuristicNode, CandidateAggregationNode, EloRankingNode, ReportGenerationNode remain unchanged) ...

class LLMSummarizerNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, analyzed_projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("Generating LLM summaries for projects...")
        updated_projects: List[Dict[str, Any]] = []

        for project in analyzed_projects:
            if project["status"] == "success":
                content_to_summarize = ""
                prompt = ""
                if project["readme_content"]:
                    content_to_summarize = project["readme_content"]
                    prompt = f"Summarize the following GitHub repository README content in 2-3 sentences, focusing on the project's purpose and key features:\n\n{content_to_summarize}"
                elif project["metadata"].get("description"):
                    content_to_summarize = project["metadata"]["description"]
                    prompt = f"Summarize the following project description in one concise sentence:\n\n{content_to_summarize}"
                else:
                    project["summary"] = "No content available to summarize for this project."
                    updated_projects.append(project)
                    continue

                try:
                    summary = call_llm(prompt)
                    project["summary"] = summary
                except Exception as e:
                    project["summary"] = f"Error generating summary from LLM: {e}"
            else:
                project["summary"] = f"Could not summarize: {project['error'] or 'Analysis failed'}"

            updated_projects.append(project)
        return updated_projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        return "default"

class ContributionNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("Calculating contribution scores (simulated)...")
        for project in projects:
            if project["status"] == "success":
                stars = project["metadata"].get("stars", 0)
                contribution_score = min(100, round(stars / 100, 2))
                project["scores"]["contribution_score"] = contribution_score
            else:
                project["scores"]["contribution_score"] = 0
        return projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        return "default"

class OriginalityNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("Calculating originality scores (simulated)...")
        for project in projects:
            if project["status"] == "success":
                is_fork = project["metadata"].get("fork", False)
                originality_score = 100 if not is_fork else random.randint(30, 70)
                project["scores"]["originality_score"] = originality_score
            else:
                project["scores"]["originality_score"] = 0
        return projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        return "default"

class TrustHeuristicNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("Calculating trust heuristic scores (simulated)...")
        for project in projects:
            if project["status"] == "success":
                trust_score_calc = 0
                if project["readme_content"] and project["summary"] and "Error generating" not in project["summary"]:
                    trust_score_calc += 30
                contrib_score = project["scores"].get("contribution_score", 0)
                orig_score = project["scores"].get("originality_score", 0)
                trust_score_calc += (contrib_score * 0.3) + (orig_score * 0.7)
                project["scores"]["trust_score"] = round(min(100, trust_score_calc), 2)
            else:
                project["scores"]["trust_score"] = 0
        return projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        return "default"

class CandidateAggregationNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        successful_project_scores: List[float] = [p["scores"]["trust_score"] for p in projects if p["status"] == "success" and "trust_score" in p["scores"]]
        overall_candidate_score = sum(successful_project_scores) / len(successful_project_scores) if successful_project_scores else 0.0
        return {"overall_candidate_score": round(overall_candidate_score, 2), "num_successful_projects": len(successful_project_scores)}

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: Dict[str, Any]) -> str:
        shared["overall_candidate_metrics"] = exec_res
        return "default"

class EloRankingNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return shared.get("overall_candidate_metrics", {})

    def exec(self, candidate_metrics: Dict[str, Any]) -> Dict[str, Any]:
        overall_score = candidate_metrics.get("overall_candidate_score", 0.0)
        min_elo, max_elo = 800, 2000
        elo_score = round(min_elo + (overall_score / 100) * (max_elo - min_elo), 2)
        candidate_metrics["elo_score"] = elo_score
        candidate_metrics["role_ranking_pool"] = "General"
        return candidate_metrics

    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> str:
        shared["overall_candidate_metrics"] = exec_res
        return "default"

class ReportGenerationNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resume_text": shared.get("resume_text", "N/A"),
            "github_project_urls": shared.get("github_project_urls", []),
            "other_urls": shared.get("other_urls", []),
            "analyzed_github_projects": shared.get("analyzed_github_projects", []),
            "overall_candidate_metrics": shared.get("overall_candidate_metrics", {})
        }

    def exec(self, report_data: Dict[str, Any]) -> str:
        logger.info("Generating candidate report...")
        report = ["# CodeCredX Candidate Report\n"]
        metrics = report_data['overall_candidate_metrics']
        report.append(f"## Candidate Overview\n**Overall Score:** {metrics.get('overall_candidate_score', 'N/A')}\n**Simulated Elo Rating:** {metrics.get('elo_score', 'N/A')}\n")
        
        report.append("\n## Analyzed Projects\n")
        for project in report_data.get('analyzed_github_projects', []):
            report.append(f"### [{project['repo_name']}]({project['url']})\n- **Status:** {project['status']}\n")
            if project.get('error'): report.append(f"- **Error:** {project['error']}\n")
            if project.get('summary'): report.append(f"- **LLM Summary:** {project['summary']}\n")
            if project.get('scores'):
                scores_str = ', '.join([f"{k}: {v}" for k, v in project['scores'].items()])
                report.append(f"- **Scores:** {scores_str}\n")
        
        return "".join(report)

    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: str) -> str:
        shared["candidate_report"] = exec_res
        report_filename = "logs/candidate_report.md"
        try:
            with open(report_filename, "w", encoding="utf-8") as f: f.write(exec_res)
            logger.info(f"Candidate report saved to {report_filename}")
        except IOError as e:
            logger.error(f"Failed to save report to file {report_filename}: {e}")
        return "default"