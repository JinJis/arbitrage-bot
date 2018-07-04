opt = ["krw_bal_after", {"factor_Settings": 1, "c": 10}, 12, 3, {"asdf": 10, "s": 5}]
hey = {
    "new": [[1234, 1], [2, 3], [4, 6]],
    "rev": [[12, 1], [2, 4], [5, 6]]
}

result = []
for trade in hey.keys():
    for time_list in hey[trade]:
        cur_time_dur = {trade: time_list}
        result.append(cur_time_dur)
        result.extend(opt)
print(result)
