import numpy as np
import matplotlib.pyplot as plt

data = [1, 1, 1, 1, 3, 3, 3, 2, 2, 4, 4, 5, 5, 5, 5, 6, 6, 6, 8, 8, 8, 8, 9, 9, 9, 9, 10]
hist = np.histogram(data, bins=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

plt.hist(data, bins=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
