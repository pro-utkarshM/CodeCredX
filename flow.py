from pocketflow import Flow
from nodes import ExtractLinksNode, GitHubAnalyzerNode

def create_flow():
    extract_node = ExtractLinksNode()
    analyzer_node = GitHubAnalyzerNode()

    extract_node >> analyzer_node  # Chain: extract → analyze

    return Flow(start=extract_node)
