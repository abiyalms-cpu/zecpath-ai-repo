from ranking_engine.ranking import rank_candidates_for_jd
from ranking_engine.shortlisting import apply_shortlisting


def top_candidates_for_jd(candidate_scores_dir, jd_file, top_n=5):
    """The ranked, zoned list a recruiter would actually look at for one role."""
    ranked = rank_candidates_for_jd(candidate_scores_dir, jd_file)
    zoned = apply_shortlisting(ranked)
    return zoned[:top_n]