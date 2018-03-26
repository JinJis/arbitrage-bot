import os


class CsvWriter:
    def __init__(self, dir_path: str, file_name: str, columns: tuple):
        # create directory named as timestamp if not already exists
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # open file with write option and write initial columns
        # `1` to select line buffering
        self.file = open("%s/%s.csv" % (dir_path, file_name), "w", 1)
        self.write_joinable(columns)

    def write_line(self, content):
        self.file.write(content + "\n")

    # joinable - list or tuple
    def write_joinable(self, joinable):
        self.write_line(",".join(map(str, joinable)))

    def close(self):
        self.file.close()
