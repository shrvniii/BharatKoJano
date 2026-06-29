def calculate_dense_ranks(results_list):
    """
    Applies dense ranking to a list of Result objects.
    Assumes the list is already sorted by score descending.
    For example: scores [50, 50, 48, 45] -> ranks [1, 1, 2, 3]
    """
    current_rank = 0
    prev_score = None
    
    for result in results_list:
        score = result.score
        if prev_score is None or score != prev_score:
            current_rank += 1
            prev_score = score
        result.rank = current_rank
        
    return results_list
