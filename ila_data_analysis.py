import numpy as np
import time
import plotly.graph_objs as go
import plotly.offline as pof
from plotly.subplots import make_subplots
from enum import Enum, auto
import pandas as pd

class DataType(Enum):
    RcfOut, DeciOut, FreqResp, BfOut, AddMuxOut = auto(), auto(), auto(), auto(), auto()

def bin2dec(bin_data, frac_bit=12):
    dec_data = 0
    if int(bin_data[0]) == 0:
        for i, s in enumerate(bin_data):
            if s == "1":
                dec_data += 2**(len(bin_data)-1-i)
        return dec_data / 2**frac_bit
    else:
        for i, s in enumerate(bin_data):
            if s == "0":
                dec_data += 2**(len(bin_data)-1-i)
        dec_data += 1
        return -dec_data / 2**frac_bit    

def parser(data, data_type):
    if data_type==DataType.BfOut:
        n_bit = 17
        n_seg = 3
    else:
        n_bit = 16
        n_seg = 4

    if data_type==DataType.AddMuxOut:
        total_n_bit = 512
    else:
        total_n_bit = 128

    if data_type==DataType.RcfOut:
        frac_bit = 15
    elif data_type==DataType.FreqResp or data_type==DataType.DeciOut:
        frac_bit = 14
    else:
        frac_bit = 13

    parsed_data = []
    for j in range(n_seg):
        lsb = total_n_bit-n_bit*2*j
        parsed_data.append(bin2dec(data[(lsb-n_bit):(lsb)], frac_bit) + 1j*bin2dec(data[(lsb-n_bit*2):(lsb-n_bit)], frac_bit))
    return parsed_data

def parse_ila_data(file_path, data_probe_name, valid_probe_name, data_type):
    df = pd.read_csv(file_path, header=None, skiprows=[1])
    df.columns = df.iloc[0].str.strip()
    df = df[1:].reset_index(drop=True)
    
    data_probe_series = df[data_probe_name].astype(str).str.strip().str.replace(' ', '')
    valid_probe_series = df[valid_probe_name].astype(str).str.strip().str.replace(' ', '')
    assert len(data_probe_series) == len(valid_probe_series)
    timestamp_len = len(data_probe_series)
    data = []
    for t in range(timestamp_len):
        if int(valid_probe_series[t]) == 1:
            data_tmp = parser(data_probe_series[t], data_type)
            for d in data_tmp:
                data.append(d)
    return np.array(data)

if __name__ == "__main__":
    font_size = 20
    bf_out = parse_ila_data(file_path="./ila_data/replica_test_case_0_bf_out.csv",
                            data_probe_name="fpga_block_design_i/datapath/system_ila_0/inst/probe0_1[127:0]",
                            valid_probe_name="fpga_block_design_i/datapath/system_ila_0/inst/probe1_1",
                            data_type=DataType.BfOut)
    figure = make_subplots(rows=2, cols=1)
    figure.add_trace(go.Scatter(y=bf_out.real), row=1, col=1)
    figure.add_trace(go.Scatter(y=bf_out.imag), row=2, col=1)
    pof.iplot(figure)
    print("DONE")