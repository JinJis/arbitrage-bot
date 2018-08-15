def make_time_list(init_time: str, final_time: str):
    cur_time = init_time
    time_list = [init_time]
    while int(cur_time[8:10]) <= int(final_time[8:10]):
        cur_time_day = cur_time[8:10]
        if int(cur_time_day) < 9:
            next_time_day = ("0%d" % (int(cur_time_day) + 1))
        else:
            next_time_day = str(int(cur_time_day) + 1)
        cur_time = cur_time[:8] + next_time_day + cur_time[10:]
        time_list.append(cur_time)

    return time_list


print(make_time_list("2018.05.01 00:00:00", "2018.05.30 00:00:00"))

