from pocketflow import Node
import re
import requests
import os

class ExtractLinksNode(Node):
    """
    Extract GitHub project URLs from simulated resume text input.
    """
    def exec(self, _):
        print("Simulating resume text input...")
        resume_text = """
        Built a secure authentication server: https://github.com/psf/requests
        Also contributed to: https://github.com/pallets/flask
        """
        return resume_text

    def post(self, shared, prep_res, exec_res):
        github_links = re.findall(r"https?://github\.com/[^\s)]+", exec_res)
        shared["project_urls"] = github_links
        print("Extracted GitHub URLs:", github_links)
        return "default"


class GitHubAnalyzerNode(Node):
    """
    For each GitHub URL:
    - Fetch repo metadata from GitHub REST API
    - Try to download the README.md from `main` or `master`
    """
    def prep(self, shared):
        return shared.get("project_urls", [])

    def exec(self, project_urls):
        headers = { "Accept": "application/vnd.github.v3+json" }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        all_data = []

        for url in project_urls:
            try:
                user_repo = "/".join(url.split("/")[-2:])
                api_url = f"https://api.github.com/repos/{user_repo}"

                # Fetch metadata
                res = requests.get(api_url, headers=headers)
                metadata = res.json()

                if res.status_code != 200 or metadata.get("private", False):
                    print(f"Skipping: {url} ({metadata.get('message', 'unknown')})")
                    continue

                # Try main/master branches for README
                readme_text = None
                for branch in ["main", "master"]:
                    readme_url = f"https://raw.githubusercontent.com/{user_repo}/{branch}/README.md"
                    r = requests.get(readme_url)
                    if r.status_code == 200:
                        readme_text = r.text
                        break

                data = {
                    "url": url,
                    "name": metadata.get("name"),
                    "description": metadata.get("description"),
                    "stars": metadata.get("stargazers_count"),
                    "fork": metadata.get("fork"),
                    "topics": metadata.get("topics", []),
                    "readme": readme_text
                }

                print(f"✔ Collected metadata for {url}")
                all_data.append(data)

            except Exception as e:
                print(f"Error analyzing {url}: {e}")

        return all_data

    def post(self, shared, prep_res, exec_res):
        shared["project_data"] = exec_res
        print("Enriched project metadata collected.")
        return "default"
