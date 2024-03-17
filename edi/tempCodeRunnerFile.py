import numpy as np
import matplotlib.pyplot as plt


X = np.arange(1, 11, 1)

Y = np.array([1, 2, 4])


lambda_val = np.linspace(0, 10, 11) / 10

def MEM_FUNC(gamma, N):
    val = gamma * abs((5 / max(N, 5)) - (N / max(N, 5)))
    if val == 0:
        return 1
    elif val >= 1:
        return 0
    else:
        return 1 - val

def check_convex(gamma, array):
    for i in lambda_val:
        for x1 in range(len(array)):
            for x2 in range(x1 + 1,len(array)):
                val1 = MEM_FUNC(gamma, X[x1] * i + X[x2] * (1 - i))
                val2 = min(MEM_FUNC(gamma, X[x1]), MEM_FUNC(gamma, X[x2]))
                if val1 < val2:
                    return False
    return True

def check_normal(array):
    for i in array:
        if i == 1:
            return True
    return False


if name == "main":
    value_table = np.zeros((3, 10))

    for i in range(len(Y)):
        for j in range(len(X)):
            value_table[i][j] = MEM_FUNC(Y[i], X[j])

    for i in range(3):
        print(f"gamma = {Y[i]}")
        print(value_table[i])
        is_normal = check_normal(value_table[i])
        is_convex = check_convex(Y[i], value_table[i])
        print()
    
        if is_normal:
            print('The fuzzy set is normal.')
        else:
            print('The fuzzy set is not normal.')
    
        if is_convex:
            print('The fuzzy set is convex.')
        else:
            print('The fuzzy set is not convex.')
        print()

    # Graph
    plt.figure(figsize=(8, 6))
    plt.plot(X, value_table[0], label="Y = 1", marker='o')
    plt.plot(X, value_table[1], label="Y = 2", marker='o')
    plt.plot(X, value_table[2], label="Y = 4", marker='o')
    plt.legend()
    plt.xticks(X)
    plt.xlabel("X values")
    plt.ylabel("Membership values")
    plt.grid(True)
    plt.show()