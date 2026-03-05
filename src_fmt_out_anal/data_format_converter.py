import math

class DataFormatConverter:
    def __init__(self, signedness = "unsigned", m = 2, n = 11):
        self.signedness = signedness
        self.m = m
        self.n = n

    def bin_to_real(self, bin_str):
        int_value = int(bin_str,2)
        if self.signedness == "signed":
            if int_value & (1<<(self.m+self.n)):
                int_value -= (1<<(self.m+self.n+1)) # 二補數轉換 (減去 2^(m+n+1))
        return int_value/(1<<self.n)


    def real_to_bin(self, real_value):
        min_val = -(1<<self.m) if self.signedness == "signed" else 0
        max_val =  (1<<self.m)-1/(1<<self.n)
        real_value = max(min(real_value, max_val), min_val)  # 限制範圍

        int_value = math.floor(real_value * (1<<self.n)) #量化模型要無條件捨去

        if self.signedness == "signed":
            if int_value < 0:
                int_value += (1<<(self.m+self.n+1))  # 轉換為二補數 (加上 2^(m+n+1))

        bin_str = f"{int_value:0b}"

        total_length = self.m + self.n + (1 if self.signedness == "signed" else 0)
        if len(bin_str) < total_length:
            bin_str = "0" * (total_length - len(bin_str)) + bin_str

        return bin_str