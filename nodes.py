# nodes.py
from pocketflow import Node
import re
import requests
import base64
import logging
import random
from typing import List, Dict, Any

# Import the utility function for LLM calls and configuration
from utils.call_llm import call_llm
from config import app_config

# Configure logging for this module
logger = logging.getLogger(__name__)

class ResumeInputNode(Node):
    def exec(self, _: Any) -> str:
        """
        Simulates reading resume content.
        For Proof of Concept (PoC), a sample resume text is hardcoded.
        In a production application, this would handle actual file parsing
        (PDF, DOCX) or integration with platforms like LinkedIn.
        """
        sample_resume_text = """
        John Doe
        Software Engineer
        Email: john.doe@example.com
        LinkedIn: https://www.linkedin.com/in/johndoe

        Projects:
        - My Awesome Project: https://github.com/octocat/Spoon-Knife
          A cool project demonstrating advanced algorithms.
        - Web Portfolio: https://johndoe.dev
          My personal website showcasing various web development projects.
        - Open Source Contribution: https://github.com/org/some-library/pull/123
          Contributed to an open-source library. (Simulated non-existent org)
        - Another Project (private/non-existent): https://github.com/johndoe/private-repo
          This should not be publicly accessible via unauthenticated requests.
        - Blog Post: https://medium.com/@johndoe/my-tech-blog-post
        - Non-existent Repo: https://github.com/nonexistentuser/nonexistentrepo12345
        - Official OpenAI Python Library: https://github.com/openai/openai-python
        """
        logger.info("Simulating resume input.")
        return sample_resume_text

    def post(self, shared: Dict[str, Any], prep_res: Any, exec_res: str) -> str:
        """
        Stores the simulated resume text in the shared store.
        """
        shared["resume_text"] = exec_res
        logger.info("Resume text stored in shared.")
        return "default"

class URLExtractionNode(Node):
    def prep(self, shared: Dict[str, Any]) -> str:
        """
        Retrieves the resume text from the shared store.
        """
        return shared.get("resume_text", "")

    def exec(self, resume_text: str) -> Dict[str, List[str]]:
        """
        Extracts URLs from the provided resume text using regular expressions.
        It specifically looks for GitHub repository links and other general URLs.
        """
        logger.info("Extracting URLs from resume text...")
        url_pattern = re.compile(r'https?://[^\s\]]+')
        found_urls = url_pattern.findall(resume_text)

        github_urls: List[str] = []
        other_urls: List[str] = []

        for url in found_urls:
            # We want the base repository URL, not specific file/folder/PR paths.
            # Handles common trailing characters like ')'
            clean_url = url.split(' ')[0].strip(')')
            match = re.match(r'(https?://github.com/[^/]+/[^/]+)', clean_url)
            if match:
                repo_url = match.group(1)
                if repo_url not in github_urls:
                    github_urls.append(repo_url)
            elif url not in other_urls:
                other_urls.append(url)

        extracted_data = {
            "github_project_urls": github_urls,
            "other_urls": other_urls
        }
        return extracted_data

    def post(self, shared: Dict[str, Any], prep_res: str, exec_res: Dict[str, List[str]]) -> str:
        """
        Stores the extracted URLs in the shared store.
        """
        shared["github_project_urls"] = exec_res["github_project_urls"]
        shared["other_urls"] = exec_res["other_urls"]
        logger.info(f"Extracted {len(exec_res['github_project_urls'])} GitHub URLs and {len(exec_res['other_urls'])} other URLs.")
        return "default"

class GitHubAnalyzerNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[str]:
        """
        Retrieves the list of GitHub project URLs from the shared store.
        """
        return shared.get("github_project_urls", [])

    def exec(self, github_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Fetches metadata and README.md for each GitHub repository URL using the GitHub API.
        Handles various API errors, including not found and forbidden access.
        """
        logger.info("Analyzing GitHub repositories...")
        analyzed_projects: List[Dict[str, Any]] = []
        github_api_base = app_config.GITHUB_API_BASE_URL

        headers = {}
        if app_config.GITHUB_TOKEN and app_config.GITHUB_TOKEN != "your-github-personal-access-token-here":
            headers["Authorization"] = f"token {app_config.GITHUB_TOKEN}"
            logger.info("Using GitHub Personal Access Token for API requests.")
        else:
            logger.warning("GitHub Personal Access Token not provided or is a placeholder. API rate limits might apply.")

        for url in github_urls:
            owner_repo_match = re.match(r'https?://github.com/([^/]+)/([^/]+)', url)
            if not owner_repo_match:
                logger.warning(f"Skipping invalid GitHub URL format: {url}")
                continue

            owner = owner_repo_match.group(1)
            repo_name = owner_repo_match.group(2)
            repo_api_url = f"{github_api_base}{owner}/{repo_name}"

            project_data: Dict[str, Any] = {
                "url": url,
                "owner": owner,
                "repo_name": repo_name,
                "status": "pending",
                "metadata": {},
                "readme_content": None,
                "error": None,
                "summary": None,
                "scores": {}
            }

            try:
                # Fetch repository metadata
                repo_response = requests.get(repo_api_url, headers=headers, timeout=10) # Add timeout
                repo_response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                repo_metadata = repo_response.json()

                project_data["metadata"] = {
                    "name": repo_metadata.get("name"),
                    "description": repo_metadata.get("description"),
                    "stars": repo_metadata.get("stargazers_count"),
                    "fork": repo_metadata.get("fork"),
                    "topics": repo_metadata.get("topics", []),
                    "visibility": "private" if repo_metadata.get("private") else "public",
                    "created_at": repo_metadata.get("created_at"),
                    "updated_at": repo_metadata.get("updated_at"),
                    "pushed_at": repo_metadata.get("pushed_at"),
                    "size": repo_metadata.get("size") # Size in KB
                }
                logger.debug(f"Fetched metadata for {owner}/{repo_name}")

                # Fetch README.md content
                readme_api_url = f"{repo_api_url}/contents/README.md"
                readme_response = requests.get(readme_api_url, headers=headers, timeout=10) # Add timeout

                if readme_response.status_code == 200:
                    readme_data = readme_response.json()
                    if readme_data.get("encoding") == "base64" and readme_data.get("content"):
                        decoded_content = base64.b64decode(readme_data["content"]).decode('utf-8')
                        project_data["readme_content"] = decoded_content
                        logger.info(f"Successfully fetched README for {owner}/{repo_name}")
                    else:
                        logger.warning(f"README found for {owner}/{repo_name} but content not in expected base64 format.")
                        project_data["error"] = "README content not in expected format."
                elif readme_response.status_code == 404:
                    logger.info(f"README.md not found for {owner}/{repo_name}.")
                    project_data["error"] = "README.md not found."
                else:
                    logger.error(f"Failed to fetch README for {owner}/{repo_name}: HTTP Status {readme_response.status_code}. Response: {readme_response.text}")
                    project_data["error"] = f"Failed to fetch README: HTTP Status {readme_response.status_code}"

                project_data["status"] = "success"

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                error_msg = f"HTTP error {status_code}: {e.response.text}"
                if status_code == 404:
                    error_msg = "Repository not found."
                elif status_code == 403:
                    error_msg = "Access forbidden (likely private repo or GitHub API rate limit exceeded). Consider using a GitHub PAT."
                logger.error(f"Error analyzing {url}: {error_msg}")
                project_data["status"] = "failed"
                project_data["error"] = error_msg
            except requests.exceptions.Timeout:
                logger.error(f"Timeout occurred while fetching data for {url}. The request took too long.")
                project_data["status"] = "failed"
                project_data["error"] = "Request timed out."
            except requests.exceptions.RequestException as e:
                error_msg = f"Network or request error for {url}: {e}"
                logger.error(error_msg)
                project_data["status"] = "failed"
                project_data["error"] = error_msg
            except Exception as e:
                error_msg = f"An unexpected error occurred during project analysis for {url}: {e}"
                logger.critical(error_msg, exc_info=True)
                project_data["status"] = "failed"
                project_data["error"] = error_msg

            analyzed_projects.append(project_data)
        return analyzed_projects

    def post(self, shared: Dict[str, Any], prep_res: List[str], exec_res: List[Dict[str, Any]]) -> str:
        """
        Stores the analyzed GitHub project data in the shared store.
        """
        shared["analyzed_github_projects"] = exec_res
        logger.info("GitHub projects analyzed and data stored in shared.")
        return "default"

class LLMSummarizerNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieves the list of analyzed GitHub projects from the shared store.
        """
        return shared.get("analyzed_github_projects", [])

    def exec(self, analyzed_projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Iterates through analyzed projects and generates a summary for each
        using an LLM, primarily from README content, or description as fallback.
        """
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
                    logger.info(f"Skipping summarization for {project['url']} due to no content.")
                    continue

                try:
                    summary = call_llm(prompt)
                    project["summary"] = summary
                    logger.info(f"Successfully summarized {project['repo_name']}")
                except Exception as e:
                    project["summary"] = f"Error generating summary from LLM: {e}"
                    logger.error(f"Failed to summarize {project['repo_name']}: {e}", exc_info=True)
            else:
                project["summary"] = f"Could not summarize: {project['error'] or 'Analysis failed'}"
                logger.info(f"Skipping summarization for failed project: {project['repo_name']}")

            updated_projects.append(project)
        return updated_projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        """
        Stores the projects with generated summaries back into the shared store.
        """
        shared["analyzed_github_projects"] = exec_res
        logger.info("Project summaries generated and stored in shared.")
        return "default"

class ContributionNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simulated calculation of contribution score.
        In a production system, this would involve cloning repositories,
        analyzing commit history (e.g., with PyDriller or GitPython),
        and determining the candidate's contribution percentage.
        """
        logger.info("Calculating contribution scores (simulated)...")
        for project in projects:
            if project["status"] == "success":
                stars = project["metadata"].get("stars", 0)
                # Simple scaling: more stars, higher contribution score. Capped at 100.
                # This is a placeholder for actual code analysis.
                contribution_score = min(100, round(stars / 100, 2))
                project["scores"]["contribution_score"] = contribution_score
                logger.info(f"  {project['repo_name']}: Contribution Score = {project['scores']['contribution_score']}")
            else:
                project["scores"]["contribution_score"] = 0
                logger.info(f"  {project['repo_name']}: Skipping contribution score due to prior failure.")
        return projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        logger.info("Contribution scores assigned.")
        return "default"

class OriginalityNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simulated calculation of originality score.
        In a production system, this would involve comparing codebases
        against templates or known forks using techniques like SimHash,
        Abstract Syntax Tree (AST) comparison, or deep learning models.
        """
        logger.info("Calculating originality scores (simulated)...")
        for project in projects:
            if project["status"] == "success":
                is_fork = project["metadata"].get("fork", False)
                # Assign a higher score if not a fork, otherwise a randomized score for forks.
                # This is a placeholder for actual code analysis.
                originality_score = 100 if not is_fork else random.randint(30, 70)
                project["scores"]["originality_score"] = originality_score
                logger.info(f"  {project['repo_name']}: Originality Score = {project['scores']['originality_score']}")
            else:
                project["scores"]["originality_score"] = 0
                logger.info(f"  {project['repo_name']}: Skipping originality score due to prior failure.")
        return projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        logger.info("Originality scores assigned.")
        return "default"

class TrustHeuristicNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simulated calculation of a trust heuristic score.
        In a production system, this meta-agent would detect spammy,
        AI-generated, or inflated projects using more complex signals,
        potentially including code quality, commit patterns, community engagement,
        and consistency checks.
        """
        logger.info("Calculating trust heuristic scores (simulated)...")
        for project in projects:
            if project["status"] == "success":
                trust_score_calc = 0
                # Bonus for good documentation and valid summary
                if project["readme_content"] and project["summary"] and \
                   "Error generating" not in project["summary"] and \
                   project["summary"] != "No content available to summarize for this project.":
                    trust_score_calc += 30

                # Incorporate existing scores with arbitrary weights (to be refined)
                contrib_score = project["scores"].get("contribution_score", 0)
                orig_score = project["scores"].get("originality_score", 0)

                trust_score_calc += (contrib_score * 0.3) + (orig_score * 0.7)

                # Cap score at 100
                project["scores"]["trust_score"] = round(min(100, trust_score_calc), 2)
                logger.info(f"  {project['repo_name']}: Trust Score = {project['scores']['trust_score']}")
            else:
                project["scores"]["trust_score"] = 0
                logger.info(f"  {project['repo_name']}: Skipping trust score due to prior failure.")
        return projects

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: List[Dict[str, Any]]) -> str:
        shared["analyzed_github_projects"] = exec_res
        logger.info("Trust heuristic scores assigned.")
        return "default"

class CandidateAggregationNode(Node):
    def prep(self, shared: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieves the list of analyzed GitHub projects with individual scores.
        """
        return shared.get("analyzed_github_projects", [])

    def exec(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates individual project scores into an overall candidate score.
        For simplicity, this averages the 'trust_score' of successful projects.
        In a real system, this would involve more complex aggregation,
        normalization across roles, and handling of various project counts.
        """
        logger.info("Aggregating candidate scores...")
        successful_project_scores: List[float] = []

        for project in projects:
            if project["status"] == "success" and "trust_score" in project["scores"]:
                successful_project_scores.append(project["scores"]["trust_score"])
            else:
                logger.info(f"  Skipping {project['repo_name']} for aggregation due to failure or missing trust score.")

        overall_candidate_score = 0.0
        if successful_project_scores:
            overall_candidate_score = sum(successful_project_scores) / len(successful_project_scores)
            logger.info(f"Calculated overall candidate score: {overall_candidate_score:.2f} (average of {len(successful_project_scores)} successful projects).")
        else:
            logger.warning("No successful projects found to aggregate scores for. Overall candidate score set to 0.")

        candidate_summary_scores = {
            "overall_candidate_score": round(overall_candidate_score, 2),
            "num_successful_projects": len(successful_project_scores),
            # Add placeholders for other aggregate metrics if needed
            # "avg_contribution_score": ...,
            # "avg_originality_score": ...,
        }
        return candidate_summary_scores

    def post(self, shared: Dict[str, Any], prep_res: List[Dict[str, Any]], exec_res: Dict[str, Any]) -> str:
        """
        Stores the aggregated candidate scores in the shared store.
        """
        shared["overall_candidate_metrics"] = exec_res
        logger.info("Overall candidate scores aggregated and stored.")
        return "default"

# NEW: Node to assign a simulated Elo score to the candidate.
class EloRankingNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieves the overall candidate metrics from the shared store.
        """
        return shared.get("overall_candidate_metrics", {})

    def exec(self, candidate_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulated Elo score calculation.
        In a real system, this would involve:
        1. Fetching the candidate's current Elo from a persistent store.
        2. Simulating pairwise comparisons against other candidates.
        3. Dynamically adjusting the Elo score based on comparison outcomes.
        4. Storing the updated Elo score back into the persistent store.

        For this simulation, we'll convert the overall_candidate_score to an Elo-like scale.
        A typical Elo scale ranges from ~400 (beginner) to ~2400+ (grandmaster).
        We'll map our 0-100 score to a range like 800-2000.
        """
        logger.info("Calculating simulated Elo score for candidate...")
        overall_score = candidate_metrics.get("overall_candidate_score", 0.0)

        # Map 0-100 score to an Elo range (e.g., 800 to 2000)
        min_elo = 800
        max_elo = 2000
        elo_score = min_elo + (overall_score / 100) * (max_elo - min_elo)
        elo_score = round(elo_score, 2)

        candidate_metrics["elo_score"] = elo_score
        logger.info(f"Simulated Elo Score: {elo_score}")

        # Placeholder for future role-specific ranking pools
        candidate_metrics["role_ranking_pool"] = "General"

        return candidate_metrics

    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> str:
        """
        Stores the updated overall candidate metrics including the Elo score.
        """
        shared["overall_candidate_metrics"] = exec_res
        logger.info("Simulated Elo score assigned and stored.")
        return "default"

# NEW: Node to generate a final report in Markdown format.
class ReportGenerationNode(Node):
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieves all relevant data for the report from the shared store.
        """
        return {
            "resume_text": shared.get("resume_text", "N/A"),
            "github_project_urls": shared.get("github_project_urls", []),
            "other_urls": shared.get("other_urls", []),
            "analyzed_github_projects": shared.get("analyzed_github_projects", []),
            "overall_candidate_metrics": shared.get("overall_candidate_metrics", {})
        }

    def exec(self, report_data: Dict[str, Any]) -> str:
        """
        Generates a comprehensive Markdown report based on the processed data.
        """
        logger.info("Generating candidate report...")
        report_content = []

        report_content.append("# CodeCredX Candidate Report\n")
        report_content.append("---\n")

        # Candidate Overview
        report_content.append("## Candidate Overview\n")
        report_content.append(f"**Overall Score:** {report_data['overall_candidate_metrics'].get('overall_candidate_score', 'N/A')}\n")
        report_content.append(f"**Simulated Elo Rating:** {report_data['overall_candidate_metrics'].get('elo_score', 'N/A')}\n")
        report_content.append(f"**Number of Successful Projects Analyzed:** {report_data['overall_candidate_metrics'].get('num_successful_projects', 'N/A')}\n")
        report_content.append(f"**Resume Snippet:**\n```\n{report_data['resume_text'][:200]}...\n```\n") # Show first 200 chars

        # Extracted URLs
        report_content.append("## Extracted URLs\n")
        report_content.append("### GitHub Project URLs:\n")
        if report_data['github_project_urls']:
            for url in report_data['github_project_urls']:
                report_content.append(f"- {url}\n")
        else:
            report_content.append("No GitHub project URLs found in resume.\n")

        report_content.append("\n### Other URLs:\n")
        if report_data['other_urls']:
            for url in report_data['other_urls']:
                report_content.append(f"- {url}\n")
        else:
            report_content.append("No other URLs found in resume.\n")

        # Analyzed Projects
        report_content.append("\n## Analyzed Projects\n")
        if report_data['analyzed_github_projects']:
            for project in report_data['analyzed_github_projects']:
                report_content.append(f"### [{project['repo_name']}]({project['url']})\n")
                report_content.append(f"- **Status:** {project['status']}\n")
                if project.get('error'):
                    report_content.append(f"- **Error:** {project['error']}\n")
                report_content.append("- **Metadata:**\n")
                for key, value in project['metadata'].items():
                    report_content.append(f"  - {key}: {value}\n")
                if project.get('summary'):
                    report_content.append(f"- **LLM Summary:** {project['summary']}\n")
                else:
                    report_content.append("- **LLM Summary:** Not available.\n")
                if project.get('scores'):
                    report_content.append("- **Scores:**\n")
                    for score_name, score_value in project['scores'].items():
                        report_content.append(f"  - {score_name}: {score_value}\n")
                else:
                    report_content.append("- **Scores:** Not assigned.\n")
                report_content.append("\n") # Add a newline for separation
        else:
            report_content.append("No GitHub projects were successfully analyzed.\n")

        full_report_content = "".join(report_content)
        logger.info("Candidate report generated successfully.")
        return full_report_content

    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: str) -> str:
        """
        Stores the generated report content in the shared store.
        Optionally, saves it to a file.
        """
        shared["candidate_report"] = exec_res
        report_filename = "logs/candidate_report.md" # Save to logs directory
        try:
            with open(report_filename, "w", encoding="utf-8") as f:
                f.write(exec_res)
            logger.info(f"Candidate report saved to {report_filename}")
        except IOError as e:
            logger.error(f"Failed to save report to file {report_filename}: {e}")

        return "default"
