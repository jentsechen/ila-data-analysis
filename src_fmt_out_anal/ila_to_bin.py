import numpy as np
import time
import plotly.graph_objs as go
import plotly.offline as pof
from plotly.subplots import make_subplots
from enum import Enum, auto
import pandas as pd
import os

class DataType(Enum):
    RcfOut, DeciOut, FreqResp, BfOut, AddMuxOut, SfOut = auto(), auto(), auto(), auto(), auto(), auto()

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

def parser(data, data_type, ch_idx):
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
    elif data_type==DataType.FreqResp:
        frac_bit = 14
    else:
        frac_bit = 13

    parsed_data = []
    for j in range(n_seg):
        lsb = total_n_bit-n_bit*2*j-ch_idx*128
        parsed_data.append(bin2dec(data[(lsb-n_bit):(lsb)], frac_bit) + 1j*bin2dec(data[(lsb-n_bit*2):(lsb-n_bit)], frac_bit))
    return parsed_data

def write_binary_string_to_file(binary_string, filename, byte_order='big'):
    """
    Converts a string of '0's and '1's into binary bytes and writes them to a file.
    """
    # 1. Validate the input string
    if not all(c in '01' for c in binary_string):
        raise ValueError("Input string must contain only '0's and '1's.")

    # 2. Convert to an integer (base 2)
    integer_value = int(binary_string, 2)
    
    # 3. Calculate required byte length and convert to bytes
    # Ensure all leading zeros are correctly handled by byte_length calculation.
    byte_length = (len(binary_string) + 7) // 8
    
    try:
        byte_data = integer_value.to_bytes(byte_length, byteorder=byte_order)
        
        # 4. Write to binary file
        with open(filename, 'wb') as f:
            f.write(byte_data)
            
        # print(f"Successfully wrote {byte_length} bytes to '{filename}' (Byte Order: {byte_order}).")
        # print(f"Hex representation: {byte_data.hex()}")

    except Exception as e:
        print(f"An error occurred: {e}")

def parse_ila_data(file_path, data_probe_name, valid_probe_name, data_type, ch_idx=0):
    df = pd.read_csv(file_path, header=None, skiprows=[1])
    df.columns = df.iloc[0].str.strip()
    df = df[1:].reset_index(drop=True)
    
    data_probe_series = df[data_probe_name].astype(str).str.strip().str.replace(' ', '')
    valid_probe_series = df[valid_probe_name].astype(str).str.strip().str.replace(' ', '')
    assert len(data_probe_series) == len(valid_probe_series)
    timestamp_len = len(data_probe_series)
    if data_type == DataType.SfOut:
        data = ""
        for t in range(timestamp_len):
            if int(valid_probe_series[t]) == 1:
                data += data_probe_series[t]
        # print(len(data))
        # write_binary_string_to_file(data, "./bins/test.bin")
        return data
    else:
        data = []
        for t in range(timestamp_len):
            if int(valid_probe_series[t]) == 1:
                data_tmp = parser(data_probe_series[t], data_type, ch_idx)
                for d in data_tmp:
                    data.append(d)
        return np.array(data)

if __name__ == "__main__":
    font_size = 20
    sync_pat = "1111100101110101001100010010010001101000111110011111100111111001"
    data = ""
    data += parse_ila_data(file_path="./ila_data/sf_out.csv",
                           data_probe_name="fpga_block_design_i/datapath/system_ila_1/inst/net_slot_2_axis_tdata[63:0]",
                           valid_probe_name="fpga_block_design_i/datapath/system_ila_1/inst/net_slot_2_axis_tvalid",
                           data_type=DataType.SfOut)
    segments = data.split(sync_pat)
    for i in range(4):
        write_binary_string_to_file(sync_pat + segments[i+1], f"./bins/output_{i}.bin")
    print("DONE")