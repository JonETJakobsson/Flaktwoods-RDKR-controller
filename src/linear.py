class linearRegressor:
    """
    Linear regression model using gradient descent.

    Parameters:
        max_iter (int, optional): Maximum number of iterations for gradient descent. Default is 1000.
        lr (float, optional): Learning rate (step size) for coefficient updates. Default is 0.01.

    Attributes:
        coeficients (list): Coefficients (weights) for the linear regression model.

    Methods:
        fit(X, y):
            Fits the linear regression model to the given data.

        Example usage:
            model = linearRegressor(max_iter=1000, lr=0.01)
            model.fit(X, y)
    """

    def __init__(self, max_iter: int = 1000, lr: float = 0.01):
        """
        Initialize the linear regression model.

        Args:
            max_iter (int, optional): Maximum number of iterations for gradient descent. Default is 1000.
            lr (float, optional): Learning rate (step size) for coefficient updates. Default is 0.01.
        """
        self.coeficients: list = None
        self.max_iter = max_iter
        self.lr = lr

    def fit(self, X: list[list], y: list):
        """
        Fit the linear regression model to the given data.

        Args:
            X (list of lists): Input features (design matrix).
            y (list): Target values.

        Returns:
            None
        """
        # Check if X is list
        if not isinstance(X[0], list):
            X = [[x] for x in X]

        # add ones to X for intercept term to work on
        X = [[1] + row for row in X]

        # add slope coeficients for each column in X
        self.coeficients = [0] * len(X[0])

        previous_mse: float = 0.0
        adjust_lr = True

        # find mean of y
        y_mean = sum(y) / len(y)

        # Gradient descent loop
        for iteration in range(self.max_iter):
            mse = 0.0
            delta_mse = 0.0
            ss_res = 0.0
            ss_tot = 0.0

            for i, row in enumerate(X):
                # Calculate prediction
                prediction = sum(x * c for x, c in zip(row, self.coeficients))

                # Calculate error
                error = prediction - y[i]
                mse += error**2

                # Update SSres and SStot
                ss_res += error**2
                ss_tot += (y[i] - y_mean) ** 2

                # Update coefficients
                for j, x in enumerate(row):
                    self.coeficients[j] -= self.lr * error * x

            # calculate mean of total SE
            mse /= len(X)

            # Calculate R-squared
            r_squared = 1 - (ss_res / ss_tot)

            print(f"Running iteration {iteration}. MSE: {mse}. R-squared: {r_squared}")

            # calculate current - previous mse
            delta_mse = mse - previous_mse
            # set current mse to previous
            previous_mse = mse

            # Adjust learning rate when getting close to an optimum
            if mse < 1e-3 and adjust_lr:
                print("Found good coefficients, adjusting learning rate.")
                self.lr /= 10
                adjust_lr = False

            if delta_mse == 0:
                print(
                    f"Found optimal coefficients, delta mse is 0. R squared is: {r_squared:.3f}"
                )
                break
