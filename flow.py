# flow.py
from pocketflow import Flow
from nodes import ResumeInputNode, URLExtractionNode, GitHubAnalyzerNode, LLMSummarizerNode, \
                    ContributionNode, OriginalityNode, TrustHeuristicNode, \
                    CandidateAggregationNode, EloRankingNode, ReportGenerationNode

def create_codecredx_flow():
    """
    Creates and returns the CodeCredX flow.
    This flow processes a resume, extracts GitHub URLs, analyzes repositories,
    generates LLM summaries, assigns simulated contribution, originality,
    and trust scores, aggregates these scores, assigns a simulated Elo ranking,
    and finally generates a comprehensive candidate report.
    Error handling for various edge cases is integrated into each node.
    """
    print("Creating CodeCredX flow...")

    # Initialize all nodes in the pipeline
    resume_input_node = ResumeInputNode()
    url_extraction_node = URLExtractionNode()
    github_analyzer_node = GitHubAnalyzerNode()
    llm_summarizer_node = LLMSummarizerNode()
    contribution_node = ContributionNode()
    originality_node = OriginalityNode()
    trust_heuristic_node = TrustHeuristicNode()
    candidate_aggregation_node = CandidateAggregationNode()
    elo_ranking_node = EloRankingNode()
    report_generation_node = ReportGenerationNode()

    # Define the sequence of nodes
    resume_input_node >> url_extraction_node
    url_extraction_node >> github_analyzer_node
    github_analyzer_node >> llm_summarizer_node
    llm_summarizer_node >> contribution_node
    contribution_node >> originality_node
    originality_node >> trust_heuristic_node
    trust_heuristic_node >> candidate_aggregation_node
    candidate_aggregation_node >> elo_ranking_node
    elo_ranking_node >> report_generation_node

    # The flow starts with the ResumeInputNode
    # This now effectively covers all core phases including integrated edge case handling.
    return Flow(start=resume_input_node)

# Create an instance of the flow for direct import if needed
codecredx_flow = create_codecredx_flow()
