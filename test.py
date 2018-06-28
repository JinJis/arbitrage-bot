rq_time_result = [4, 5, 8, 9, 10, 11, 16, 17, 18, 19, 24, 25, 30, 55, 57, 59, 60, 61, 62, 63, 64, 65, 70, 75, 76]
time_interval = 1

was_in_oppty = False
rq_time_set = list()
final_result = list()

for index, item in enumerate(rq_time_result[1:]):
    now = rq_time_result[index + 1]
    before = rq_time_result[index]
    # when in oppty
    if now - before == time_interval:
        if not was_in_oppty:
            was_in_oppty = True
            rq_time_set.append(before)
    else:
        if was_in_oppty:
            was_in_oppty = False
            rq_time_set.append(before)
            final_result.append([i for i in rq_time_set])
            rq_time_set.clear()

if was_in_oppty:
    rq_time_set.append(rq_time_result[-1])
    final_result.append([i for i in rq_time_set])
    rq_time_set.clear()


print(final_result)

