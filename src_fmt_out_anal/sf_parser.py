from DataSourceFormat import SF_ECHO_HEADER,SF_REPLICA_HEADER, hexdump, DataChunk
import json
import os
from pathlib import Path
import argparse


SFSY = "F975312468F9F9F9"
ECHO_HEADER_BYTE_W = 75
REPLICA_HEADER_BYTE_W = 18
SERDES_OUT_BYTE_W = 8

def parse_sf_bin(bin_name, bin_file_path, out_folder):
    f = open(bin_file_path, 'rb')
    if not os.path.exists(out_folder): 
        os.makedirs(out_folder) 
    pulse_num = 0
    while(1):
        pkg_start = f.tell()
        SFSY_check = f.read(8)
        # print(SFSY_check)
        if SFSY_check != bytes.fromhex(SFSY): break
        # binary_string = ''.join(format(byte, '08b') for byte in SFSY_check)
        # hex_str = hex(int(binary_string, 2))[2:].upper()
        # print(hex_str)

        SFID_check = f.read(1)
        binary_string = ''.join(format(byte, '08b') for byte in SFID_check)
        echo_rep_ctrl = binary_string[4]
        # hex_str = hex(int(binary_string, 2))[2:].upper()
        # print(binary_string[4])

        f.seek(pkg_start)

        sf_dic = {}

        if echo_rep_ctrl == "0":
            #parse header
            header = f.read(ECHO_HEADER_BYTE_W)
            sf_header = SF_ECHO_HEADER.deserialize(header)
            header_dic = SF_ECHO_HEADER.parse(sf_header)
            sf_dic.update(header_dic)
            # print(header_dic)

            #parse data field
            data_field_read_depth = ((sf_header.SFLN-1)//(SERDES_OUT_BYTE_W*8)+1)*8-ECHO_HEADER_BYTE_W
            data_field = f.read(data_field_read_depth)
            dc = DataChunk.deserialize(
                buffer=data_field,
                compression=sf_header.compression,
                iq_config=sf_header.SFID & 0b11,
                block_size_mode=sf_header.block_size_mode,
                word_length_mode=sf_header.word_length_mode,
                num_block=sf_header.num_block
            )
            sf_dic.update(dc)

            out_json_file = os.path.join(out_folder, f"{bin_name}_p{pulse_num}.json")
            with open(out_json_file, "w") as json_file:
                json.dump(sf_dic, json_file, indent=4)

            pulse_num+=1

        else:
            #parse header
            header = f.read(REPLICA_HEADER_BYTE_W)
            sf_header = SF_REPLICA_HEADER.deserialize(header)
            header_dic = SF_REPLICA_HEADER.parse(sf_header)
            sf_dic.update(header_dic)

            #parse data field
            data_field_read_depth = ((sf_header.SFLN-1)//(SERDES_OUT_BYTE_W*8)+1)*8-REPLICA_HEADER_BYTE_W
            data_field = f.read(data_field_read_depth)
            # print(data_field_read_depth)
            # print(f.tell())
            dc = DataChunk.deserialize_rep(
                buffer=data_field,
                iq_config=sf_header.SFID & 0b11,
                num_sample_rep = sf_header.NumSample_Rep
            )
            sf_dic.update(dc)

            ReplicaFlag = "A" if sf_header.ReplicaFlag == 0 \
                     else "B" if sf_header.ReplicaFlag == 1 \
                     else "C" if sf_header.ReplicaFlag == 2 \
                     else "D"
            out_json_file = os.path.join(out_folder, f"{bin_name}_p{pulse_num}_rep_{ReplicaFlag}.json")
            with open(out_json_file, "w") as json_file:
                json.dump(sf_dic, json_file, indent=4)

def main():
    parser = argparse.ArgumentParser(description="SF Parser of bin files")
    parser.add_argument("--bin_dir", type=str, default="./bins", help="Enter the input bin dir")
    parser.add_argument("--out_json_dir", type=str, default="./out_json", help="Enter the input bin dir")
    args = parser.parse_args()

    if not os.path.exists(args.out_json_dir): 
        os.makedirs(args.out_json_dir) 
    for file in Path(args.out_json_dir).rglob("*.json"): 
        file.unlink()
        print(f"Deleted old json files: {file}")

    bin_files = [f for f in os.listdir(args.bin_dir) if f.endswith(".bin")]

    for bin_file in bin_files:
        file_path = os.path.join(args.bin_dir, bin_file)
        bin_name = Path(bin_file).stem
        print(f"Parsing file {bin_file}...")
        parse_sf_bin(bin_name, file_path, args.out_json_dir)

    print("Parse complete!")
    print(f"Results are stored in {args.out_json_dir}")


if __name__ == "__main__":
    main()


    

