"""
Takes the structured job entries from experience_parser.py and computes:
  - total experience (merging overlapping date ranges so they aren't
    double-counted)
  - gaps between jobs (unexplained time with no role at all)
  - overlaps between jobs (two roles whose date ranges actually cross,
    e.g. a side role held while still employed elsewhere)

Only adjacent jobs (by start date) are compared for gaps/overlaps — a
three-way overlap wouldn't be caught by this. That's a known limit, not
a silent guess, and is noted in the write-up.
"""

from datetime import datetime


def _month_index(year, month):
    """Turns (2024, 1) into a single comparable integer."""
    return year * 12 + month


def _job_range(job, reference_date):
    start_idx = _month_index(job["start_year"], job["start_month"])
    if job["is_current"] or job["end_year"] is None:
        end_idx = _month_index(reference_date.year, reference_date.month)
    else:
        end_idx = _month_index(job["end_year"], job["end_month"])
    return start_idx, end_idx


def total_experience_months(jobs, reference_date=None):
    """
    Total experience across all jobs, in months, with overlapping date
    ranges merged first so time spent in two roles at once isn't counted
    twice.
    """
    if not jobs:
        return 0
    if reference_date is None:
        reference_date = datetime.now()

    ranges = sorted(_job_range(job, reference_date) for job in jobs)
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:  # overlaps (or touches) the previous range
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return sum(end - start + 1 for start, end in merged)


def format_duration(total_months):
    """123 -> (10, 3) meaning 10 years, 3 months."""
    years, months = divmod(total_months, 12)
    return years, months


def find_gaps_and_overlaps(jobs, reference_date=None, gap_threshold_months=1):
    """
    Walks consecutive jobs in chronological order (by start date) and
    flags a gap when there's unexplained time between one job ending and
    the next starting, or an overlap when two jobs' ranges actually cross.
    """
    if reference_date is None:
        reference_date = datetime.now()
    if len(jobs) < 2:
        return [], []

    enriched = sorted(
        ((job, *_job_range(job, reference_date)) for job in jobs),
        key=lambda item: item[1],
    )

    gaps = []
    overlaps = []
    for (job_a, start_a, end_a), (job_b, start_b, end_b) in zip(enriched, enriched[1:]):
        if start_b <= end_a:
            overlaps.append({
                "job_a": job_a["raw_line"],
                "job_b": job_b["raw_line"],
                "overlap_months": end_a - start_b + 1,
            })
        else:
            gap_months = start_b - end_a - 1
            if gap_months >= gap_threshold_months:
                gaps.append({
                    "after_job": job_a["raw_line"],
                    "before_job": job_b["raw_line"],
                    "gap_months": gap_months,
                })

    return gaps, overlaps