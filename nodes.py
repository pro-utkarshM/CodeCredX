# nodes.py
from pocketflow import Node
import re
import requests
import base64 # To decode base64 content from GitHub API
import os     # To access environment variables for API keys

# Import the utility function for LLM calls
from utils.call_llm import call_llm

# This node simulates accepting resume content as plain text.
# In a full implementation, this would handle PDF, DOCX, or LinkedIn parsing.
class ResumeInputNode(Node):
    def exec(self, _):
        """
        Simulates reading resume content.
        For Proof of Concept (PoC), a sample resume text is hardcoded.
        In a real application, this would read from a file or another input source.
        """
        # Sample resume text containing GitHub and other project URLs.
        sample_resume_text = """
        John Doe
        Software Engineer
        Email: john.doe@example.com
        LinkedIn: https://www.linkedin.com/in/johndoe

        Projects:
        - My Awesome Project: https://github.com/octocat/Spoon-Knife
          A cool project demonstrating advanced algorithms. (This is a real GitHub repo for testing)
        - Web Portfolio: https://johndoe.dev
          My personal website showcasing various web development projects.
        - Open Source Contribution: https://github.com/org/some-library/pull/123
          Contributed to an open-source library.
        - Another Project (private - will cause error without auth): https://github.com/johndoe/private-repo
          This should not be publicly accessible via unauthenticated requests.
        - Blog Post: https://medium.com/@johndoe/my-tech-blog-post
        - Non-existent Repo: https://github.com/nonexistentuser/nonexistentrepo12345
        - Another public example: https://github.com/openai/openai-python
        """
        print("Simulating resume input...")
        return sample_resume_text

    def post(self, shared, prep_res, exec_res):
        """
        Stores the simulated resume text in the shared store.
        """
        shared["resume_text"] = exec_res
        print("Resume text stored in shared.")
        return "default" # CORRECTED: Return a string, not the shared dict

# This node extracts URLs (especially GitHub URLs) from the resume text.
class URLExtractionNode(Node):
    def prep(self, shared):
        """
        Retrieves the resume text from the shared store.
        """
        return shared.get("resume_text", "")

    def exec(self, resume_text):
        """
        Extracts URLs from the provided resume text using regular expressions.
        It specifically looks for GitHub repository links.
        """
        print("Extracting URLs from resume text...")
        # Regex to find URLs. This can be refined to be more specific.
        # This regex broadly matches http/https URLs.
        url_pattern = re.compile(r'https?://[^\s\]]+')
        found_urls = url_pattern.findall(resume_text)

        github_urls = []
        other_urls = []

        for url in found_urls:
            # Simple check for GitHub repository URLs (ignoring pull requests, etc.)
            # We want the base repository URL, not specific file/folder/PR paths.
            match = re.match(r'(https?://github.com/[^/]+/[^/]+)', url.split(' ')[0].strip(')'))
            if match:
                repo_url = match.group(1)
                if repo_url not in github_urls: # Add only unique base repo URLs
                    github_urls.append(repo_url)
            elif url not in other_urls: # Add unique non-github URLs
                other_urls.append(url)

        extracted_data = {
            "github_project_urls": github_urls,
            "other_urls": other_urls
        }
        return extracted_data

    def post(self, shared, prep_res, exec_res):
        """
        Stores the extracted URLs in the shared store.
        """
        shared["github_project_urls"] = exec_res["github_project_urls"]
        shared["other_urls"] = exec_res["other_urls"]
        print(f"Extracted {len(exec_res['github_project_urls'])} GitHub URLs and {len(exec_res['other_urls'])} other URLs.")
        print(f"DEBUG: shared['github_project_urls'] after URLExtractionNode.post: {shared['github_project_urls']}")
        return "default" # CORRECTED: Return a string, not the shared dict

# This node fetches metadata and README content from GitHub repositories.
class GitHubAnalyzerNode(Node):
    def prep(self, shared):
        """
        Retrieves the list of GitHub project URLs from the shared store.
        """
        print(f"DEBUG: shared['github_project_urls'] at start of GitHubAnalyzerNode.prep: {shared.get('github_project_urls')}")
        return shared.get("github_project_urls", [])

    def exec(self, github_urls):
        """
        Fetches metadata and README.md for each GitHub repository URL.
        Handles invalid, private, or inaccessible repositories.
        """
        print("Analyzing GitHub repositories...")
        analyzed_projects = []
        github_api_base = "https://api.github.com/repos/"

        github_token = os.environ.get("GITHUB_TOKEN")
        headers = {"Authorization": f"token {github_token}"} if github_token else {}

        try:
            for url in github_urls:
                owner_repo_match = re.match(r'https?://github.com/([^/]+)/([^/]+)', url)
                if not owner_repo_match:
                    print(f"Skipping invalid GitHub URL format: {url}")
                    continue

                owner = owner_repo_match.group(1)
                repo_name = owner_repo_match.group(2)
                repo_api_url = f"{github_api_base}{owner}/{repo_name}"
                project_data = {
                    "url": url,
                    "owner": owner,
                    "repo_name": repo_name,
                    "status": "pending",
                    "metadata": {},
                    "readme_content": None,
                    "error": None,
                    "summary": None # Initialize summary here
                }

                try:
                    # Fetch repository metadata
                    repo_response = requests.get(repo_api_url, headers=headers)
                    repo_response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                    repo_metadata = repo_response.json()

                    project_data["metadata"] = {
                        "name": repo_metadata.get("name"),
                        "description": repo_metadata.get("description"),
                        "stars": repo_metadata.get("stargazers_count"),
                        "fork": repo_metadata.get("fork"),
                        "topics": repo_metadata.get("topics", []),
                        "visibility": "private" if repo_metadata.get("private") else "public"
                    }

                    # Fetch README.md content
                    readme_api_url = f"{repo_api_url}/contents/README.md"
                    readme_response = requests.get(readme_api_url, headers=headers)

                    if readme_response.status_code == 200:
                        readme_data = readme_response.json()
                        if readme_data.get("encoding") == "base64" and readme_data.get("content"):
                            decoded_content = base64.b64decode(readme_data["content"]).decode('utf-8')
                            project_data["readme_content"] = decoded_content
                            print(f"Successfully fetched README for {owner}/{repo_name}")
                        else:
                            print(f"README found for {owner}/{repo_name} but content not in expected base64 format.")
                            project_data["error"] = "README content not in expected format."
                    elif readme_response.status_code == 404:
                        print(f"README.md not found for {owner}/{repo_name}.")
                        project_data["error"] = "README.md not found."
                    else:
                        print(f"Failed to fetch README for {owner}/{repo_name}: {readme_response.status_code}")
                        project_data["error"] = f"Failed to fetch README: {readme_response.status_code}"

                    project_data["status"] = "success"

                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code
                    if status_code == 404:
                        error_msg = "Repository not found."
                    elif status_code == 403:
                        error_msg = "Access forbidden (likely private or rate limit exceeded). Consider using a GitHub PAT)."
                    else:
                        error_msg = f"HTTP error {status_code}: {e.response.text}"
                    print(f"Error analyzing {url}: {error_msg}")
                    project_data["status"] = "failed"
                    project_data["error"] = error_msg
                except requests.exceptions.RequestException as e:
                    error_msg = f"Network or request error: {e}"
                    print(f"Error analyzing {url}: {error_msg}")
                    project_data["status"] = "failed"
                    project_data["error"] = error_msg
                except Exception as e:
                    error_msg = f"An unexpected error occurred during project analysis: {e}"
                    print(f"Error analyzing {url}: {error_msg}")
                    project_data["status"] = "failed"
                    project_data["error"] = error_msg

                analyzed_projects.append(project_data)

            return analyzed_projects
        except Exception as e:
            print(f"CRITICAL ERROR in GitHubAnalyzerNode.exec: {e}")
            return []

    def post(self, shared, prep_res, exec_res):
        """
        Stores the analyzed GitHub project data in the shared store.
        """
        shared["analyzed_github_projects"] = exec_res
        print("GitHub projects analyzed and data stored in shared.")
        print(f"DEBUG: shared['github_project_urls'] after GitHubAnalyzerNode.post: {shared.get('github_project_urls')}")
        return "default" # CORRECTED: Return a string, not the shared dict

# This node uses an LLM to summarize the content of each analyzed GitHub project.
class LLMSummarizerNode(Node):
    def prep(self, shared):
        """
        Retrieves the list of analyzed GitHub projects from the shared store.
        """
        print(f"DEBUG: shared['github_project_urls'] at start of LLMSummarizerNode.prep: {shared.get('github_project_urls')}")
        return shared.get("analyzed_github_projects", [])

    def exec(self, analyzed_projects):
        """
        Iterates through analyzed projects and generates a summary for each
        using an LLM, primarily from README content, or description as fallback.
        """
        print("Generating LLM summaries for projects...")
        updated_projects = []

        try:
            for project in analyzed_projects:
                if project["status"] == "success":
                    content_to_summarize = ""
                    if project["readme_content"]:
                        content_to_summarize = project["readme_content"]
                        prompt = f"Summarize the following GitHub repository README content in 2-3 sentences, focusing on the project's purpose and key features:\n\n{content_to_summarize}"
                    elif project["metadata"].get("description"):
                        content_to_summarize = project["metadata"]["description"]
                        prompt = f"Summarize the following project description in one concise sentence:\n\n{content_to_summarize}"
                    else:
                        project["summary"] = "No content available to summarize for this project."
                        updated_projects.append(project)
                        print(f"Skipping summarization for {project['url']} due to no content.")
                        continue

                    try:
                        print(f"Calling LLM for summarization of {project['url']}...")
                        summary = call_llm(prompt)
                        project["summary"] = summary
                        print(f"Successfully summarized {project['url']}")
                    except Exception as e:
                        project["summary"] = f"Error generating summary from LLM: {e}"
                        print(f"Failed to summarize {project['url']}: {e}")
                else:
                    project["summary"] = f"Could not summarize: {project['error'] or 'Analysis failed'}"
                    print(f"Skipping summarization for failed project: {project['url']}")

                updated_projects.append(project)
            return updated_projects
        except Exception as e:
            print(f"CRITICAL ERROR in LLMSummarizerNode.exec: {e}")
            return []
    def post(self, shared, prep_res, exec_res):
        """
        Stores the projects with generated summaries back into the shared store.
        """
        shared["analyzed_github_projects"] = exec_res
        print("Project summaries generated and stored in shared.")
        print(f"DEBUG: shared['github_project_urls'] after LLMSummarizerNode.post: {shared.get('github_project_urls')}")
        return "default" # CORRECTED: Return a string, not the shared dict
