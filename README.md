## How to Run
```parsed_data = parse_ila_data(file_path, data_probe_name, valid_probe_name, data_type)```
|input|type|description|
|:--:|:--:|:--:|
|file_path|str|csv file path of ILA|
|data_probe_name|str||
|valid_probe_name|str||
|data_type|DataType||

## Data Format
|DataType|data format|fixed-point format|remark|
|:--:|:--:|:--:|:--:|
|RcfOut|{$p_3$, $p_2$, $p_1$, $p_0$}|$p_i$: 32 bits, {Q, I} = {s0.13, 2’d0, s0.13, 2’d0}, $i=0\sim3$|to be check|
|FreqResp|{96'd0, $p_0$}|$p_0$: 32 bits, {Q, I} = {s1.14, s1.14}|to be check|
|BfOut|{26'd0, $p_2$, $p_1$, $p_0$}|$p_i$: 34 bits, {Q, I} = {s3.13, s3.13}, $i=0\sim2$|
|DeciOut|{$p_3$, $p_2$, $p_1$, $p_0$}|$p_i$: 32 bits, {Q, I} = {s2.13, s2.13}, $i=0\sim3$|
|AddMuxOut|{$p_3^3$, $p_2^3$, $p_1^3$, $p_0^3$, $p_3^2$, $p_2^2$, $p_1^2$, $p_0^2$, $p_3^1$, $p_2^1$, $p_1^1$, $p_0^1$, $p_3^0$, $p_2^0$, $p_1^0$, $p_0^0$}|$p_i^j$: 32 bits, {Q, I} = {s1.14, s1.14}, $i=0\sim3,j=0\sim3$|to be check, $j$ stands for channel index, only channel 0 is considered in this analyzer|
