def dp_differ(manual_tokens: list[str], ocr_tokens: list[str]) -> list[tuple[str, str]]:
    # DP table for minimal edit distance
    m, n = len(manual_tokens), len(ocr_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if manual_tokens[i - 1] == ocr_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j],    # delete
                                   dp[i][j - 1],    # insert
                                   dp[i - 1][j - 1]) # substitute

    # Backtrack to get the diff
    i, j = m, n
    diff = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and manual_tokens[i - 1] == ocr_tokens[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + 1):
            diff.append(("delete", manual_tokens[i - 1]))
            i -= 1
        elif j > 0 and (i == 0 or dp[i][j] == dp[i][j - 1] + 1):
            diff.append(("insert", ocr_tokens[j - 1]))
            j -= 1
        else:
            # Replace: show both manual and ocr token
            diff.append(("replace", manual_tokens[i - 1], ocr_tokens[j - 1]))
            i -= 1
            j -= 1
    diff.reverse()

    diff = [
        f"{token_diff[1]} inserted" if token_diff[0] == 'insert' else
        f"{token_diff[1]} deleted" if token_diff[0] == 'delete' else
        normalize_substitution(token_diff[2], token_diff[1]) if token_diff[0] == 'replace' else None
        for token_diff in diff
    ]

    return diff
