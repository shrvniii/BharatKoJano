import csv

def build_rankings_csv(results, file_object):
    """
    Writes all results with ranking information into a CSV file object.
    """
    writer = csv.writer(file_object)
    
    # Headers
    writer.writerow([
        'Rank',
        'Roll Number',
        'Full Name',
        'School',
        'Group',
        'Paper Set',
        'Score',
        'Percentage',
        'Unanswered Questions',
        'Multi-Marked Questions',
        'Evaluated At'
    ])
    
    # Data Rows
    for r in results:
        writer.writerow([
            r.rank,
            r.participant.roll_number,
            r.participant.full_name,
            r.participant.school.name,
            r.participant.get_group_display(),
            r.participant.get_paper_set_display(),
            r.score,
            f"{r.percentage}%",
            r.unanswered_count,
            r.multi_marked_count,
            r.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
