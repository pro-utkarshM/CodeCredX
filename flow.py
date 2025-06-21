# flow.py
from pocketflow import Flow
# Import all necessary nodes for the complete flow, including the new Elo ranking node
from nodes import ResumeInputNode, URLExtractionNode, GitHubAnalyzerNode, LLMSummarizerNode, \
                    ContributionNode, OriginalityNode, TrustHeuristicNode, \
                    CandidateAggregationNode, EloRankingNode # NEW Node

def create_codecredx_flow():
    """
    Creates and returns the CodeCredX flow.
    This flow processes a resume, extracts GitHub URLs, analyzes repositories,
    generates LLM summaries, assigns simulated contribution, originality,
    and trust scores, aggregates these scores, and finally assigns a simulated Elo ranking.
    """
    print("Creating CodeCredX flow...") # Keep this top-level print for immediate feedback

    # Initialize all nodes in the pipeline
    resume_input_node = ResumeInputNode()
    url_extraction_node = URLExtractionNode()
    github_analyzer_node = GitHubAnalyzerNode()
    llm_summarizer_node = LLMSummarizerNode()
    contribution_node = ContributionNode()
    originality_node = OriginalityNode()
    trust_heuristic_node = TrustHeuristicNode()
    candidate_aggregation_node = CandidateAggregationNode()
    elo_ranking_node = EloRankingNode() # NEW: Elo Ranking Node

    # Define the sequence of nodes
    # ... -> TrustHeuristic -> CandidateAggregation -> EloRanking
    resume_input_node >> url_extraction_node
    url_extraction_node >> github_analyzer_node
    github_analyzer_node >> llm_summarizer_node
    llm_summarizer_node >> contribution_node
    contribution_node >> originality_node
    originality_node >> trust_heuristic_node
    trust_heuristic_node >> candidate_aggregation_node
    candidate_aggregation_node >> elo_ranking_node # Chain the new Elo ranking node

    # The flow starts with the ResumeInputNode
    # This now covers Phase 0, Phase 1, Phase 2, Phase 3, and Phase 4.
    return Flow(start=resume_input_node)

# Create an instance of the flow for direct import if needed
codecredx_flow = create_codecredx_flow()
