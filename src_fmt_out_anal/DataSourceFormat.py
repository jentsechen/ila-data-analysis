
from enum import IntEnum
import numpy as np
from recordclass import recordclass

import random
random.seed(0) 
from data_format_converter import DataFormatConverter

class BitField():
    def __init__(self, name, lsb, length):
        self.name = name
        self.lsb = lsb
        self.length = length
        self.msb = self.lsb + self.length -1

class ByteField():
    def __init__(self, name, lsb, length):
        self.name = name
        self.lsb = lsb*8
        self.length = length*8
        self.msb = self.lsb + self.length -1

def helper_serialize(buffer, data_in, lsb, bitlength):
    start_pos = lsb%8
    bitlength_remaining = bitlength
    cur_pos = 0
    for byte_count in range(lsb//8, (lsb+bitlength-1)//8+1):
        mask_bits = bitlength_remaining if (bitlength_remaining + start_pos) < 8 else (8 - start_pos)
        data = (data_in >> cur_pos) & ((1 << mask_bits) -1)

        buffer[byte_count] |= data << start_pos

        start_pos = 0
        cur_pos += mask_bits
        bitlength_remaining -= mask_bits

def helper_deserialize(buffer, lsb, bitlength):
    val = 0

    start_pos = lsb%8
    bitlength_remaining = bitlength
    for byte_count in range(lsb//8, (lsb+bitlength-1)//8+1):
        mask_bits = (8-start_pos) if (bitlength_remaining+start_pos) > 8 else bitlength_remaining
        data = ((buffer[byte_count] >> (8-mask_bits-start_pos)) & ( (1<<mask_bits) - 1) ) 
        
        val = data | val << mask_bits if (byte_count != lsb//8) else data | val << mask_bits 
        start_pos = 0
        bitlength_remaining -=  mask_bits
    
    return val

class E_COMPRESSION(IntEnum):
    BYPASS = 0
    BAQ = 1
    BFPQ = 2
    FBAQ = 3

BLOCK_SIZE_MAP = {
    E_COMPRESSION.BYPASS:{
        0: 8,
        1: 16,
        2: 32,
        3: 64,
    },
    E_COMPRESSION.BAQ:{
        0: 128,
        1: 256,
        2: 512,
        3: None,
    },
    E_COMPRESSION.BFPQ:{
        0: 8,
        1: 16,
        2: 32,
        3: None,
    },
}

WORD_LENGTH_MAP = {
    E_COMPRESSION.BYPASS:{
        0: 14,
    },
    E_COMPRESSION.BAQ:{
        0: 2,
        1: 3,
        2: 4,
        3: 6,
        4: 8,
    },
    E_COMPRESSION.BFPQ:{
        0: 2,
        1: 3,
        2: 4,
        3: 6,
        4: 8,
    },
}

HEADER_LENGTH_MAP = {
    E_COMPRESSION.BYPASS: 2,
    E_COMPRESSION.BAQ: 11,
    E_COMPRESSION.BFPQ: 8,
}

class DataChunk():
    def __init__(
        self, 
        iq_config = 0,
        compression = 0,
        block_size_mode = 0,
        word_length_mode = 0,
        num_block = 0,
        num_sample_rep = 0):
        self.compression = E_COMPRESSION(compression)
        self.block_size = BLOCK_SIZE_MAP[self.compression][block_size_mode]
        self.word_length = WORD_LENGTH_MAP[self.compression][word_length_mode]
        self.header_length = HEADER_LENGTH_MAP[self.compression]
        self.iq_config = iq_config
        self.num_block = num_block
        self.num_sample_rep = num_sample_rep

    @staticmethod
    def deserialize(       
        buffer,
        iq_config,
        compression,
        block_size_mode,
        word_length_mode,
        num_block
        ):

        dc = DataChunk(
            iq_config=iq_config,
            compression=compression,
            block_size_mode=block_size_mode,
            word_length_mode=word_length_mode,
            num_block=num_block
        )

        data_field_list = []
        data_field_dic = {}
        data_block_list = []
        data_block_list_I = []
        data_block_list_Q = []
        data_block_dic = {}

        for i in range(num_block):
            for j in range(dc.block_size):
                if (iq_config == 0b01 or iq_config == 0b10):
                    #print block header
                    if j == 0:
                        bit_msb_pos = i*(dc.header_length+ dc.block_size*dc.word_length)
                        header=helper_deserialize(buffer, bit_msb_pos, dc.header_length)
                        assert((i)&0b11 == helper_deserialize(buffer, bit_msb_pos, 2)), \
                         f"{helper_deserialize(buffer, bit_msb_pos, 2)} != {(i)&0b11}(expected)"
                    # print block data
                    bit_msb_pos = dc.header_length + j*dc.word_length + i*(dc.header_length+ dc.block_size*dc.word_length)
                    # if(iq_config == 0b01): print(f"block [{i}] data I [{j}] = {hex(helper_deserialize(buffer, bit_msb_pos, dc.word_length))}")
                    # if(iq_config == 0b10): print(f"block [{i}] data Q [{j}] = {hex(helper_deserialize(buffer, bit_msb_pos, dc.word_length))}")
                    data_block_list.append(helper_deserialize(buffer, bit_msb_pos, dc.word_length))

                else:
                    #print block header
                    if j == 0:
                        bit_msb_pos = i*(dc.header_length+ dc.block_size*2*dc.word_length)
                        header=helper_deserialize(buffer, bit_msb_pos, dc.header_length)

                        #================================================#
                        val_from_i = i & 0b11
                        val_from_buf = helper_deserialize(buffer, bit_msb_pos, 2)

                        # print(f"Expected bits from i: {val_from_i}, but got from buffer: {val_from_buf}, and num_block is {i}")
                        assert(val_from_i == val_from_buf)
                        #================================================#


                        assert((i)&0b11 == helper_deserialize(buffer, bit_msb_pos, 2))

                    # print block data
                    bit_msb_pos = dc.header_length + j*2*dc.word_length + i*(dc.header_length+ dc.block_size*2*dc.word_length)
                    data_block_list_I.append(helper_deserialize(buffer, bit_msb_pos, dc.word_length))
                    bit_msb_pos = dc.header_length + (j*2+1)*dc.word_length + i*(dc.header_length+ dc.block_size*2*dc.word_length)
                    data_block_list_Q.append(helper_deserialize(buffer, bit_msb_pos, dc.word_length))

            
            #parse data field
            if(compression == 0): 
                s2_11_converter = DataFormatConverter(signedness = "signed", m = 2, n = 11)
                if(iq_config == 0b01): 
                    # s2_11_converter.bin_to_real
                    data_block_dic['BypassOutI'] = [s2_11_converter.bin_to_real(bin(data_block_list[i])) for i in range(len(data_block_list))]
                elif(iq_config == 0b10): 
                    data_block_dic['BypassOutQ'] = [s2_11_converter.bin_to_real(bin(data_block_list[i])) for i in range(len(data_block_list))]
                else:
                    data_block_dic['BypassOutI'] = [s2_11_converter.bin_to_real(bin(data_block_list_I[i])) for i in range(len(data_block_list_I))]
                    data_block_dic['BypassOutQ'] = [s2_11_converter.bin_to_real(bin(data_block_list_Q[i])) for i in range(len(data_block_list_Q))]
            elif(compression == 1): 
                if(iq_config == 0b01): 
                    data_block_dic['BAQOutI'] = data_block_list
                elif(iq_config == 0b10): 
                    data_block_dic['BAQOutQ'] = data_block_list
                else:
                    data_block_dic['BAQOutI'] = data_block_list_I
                    data_block_dic['BAQOutQ'] = data_block_list_Q
                data_block_dic["FVarianceAddress"] = (header>>1)&0xFF
                data_block_dic["fOverFlow"] = header&0x1
            else: 
                if(iq_config == 0b01): 
                    data_block_dic['MantissaI'] = []
                    for data in data_block_list:
                        Mantissa = data & ((1 << (dc.word_length-1)) - 1)
                        data_block_dic['MantissaI'].append(Mantissa)
                elif(iq_config == 0b10): 
                    data_block_dic['MantissaQ'] = []
                    for data in data_block_list:
                        Mantissa = data & ((1 << (dc.word_length-1)) - 1)
                        data_block_dic['MantissaQ'].append(Mantissa)
                else:
                    data_block_dic['MantissaI'] = []
                    data_block_dic['MantissaQ'] = []
                    for dataI,dataQ in zip(data_block_list_I,data_block_list_Q):
                        MantissaI = dataI & ((1 << (dc.word_length-1)) - 1)
                        MantissaQ = dataQ & ((1 << (dc.word_length-1)) - 1)
                        data_block_dic['MantissaI'].append(MantissaI)
                        data_block_dic['MantissaQ'].append(MantissaQ)
                data_block_dic["ce"] = (header>>3)&0x7
                data_block_dic["cw"] = header&0x7
                if(iq_config == 0b01): 
                    data_block_dic['signI'] = []
                    for data in data_block_list:
                        Sign = (data >> (dc.word_length-1)) & 0x1
                        data_block_dic['signI'].append(Sign)
                elif(iq_config == 0b10): 
                    data_block_dic['signQ'] = []
                    for data in data_block_list:
                        Sign = (data >> (dc.word_length-1)) & 0x1
                        data_block_dic['signQ'].append(Sign)
                else:
                    data_block_dic['signI'] = []
                    data_block_dic['signQ'] = []
                    for dataI,dataQ in zip(data_block_list_I,data_block_list_Q):
                        SignI = (dataI >> (dc.word_length-1)) & 0x1
                        SignQ = (dataQ >> (dc.word_length-1)) & 0x1
                        data_block_dic['signI'].append(SignI)
                        data_block_dic['signQ'].append(SignQ)

            data_field_list.append(data_block_dic)  
            data_block_list = []
            data_block_list_I = []
            data_block_list_Q = []
            data_block_dic = {}

        data_field_dic['data_field'] = data_field_list

        return data_field_dic
    
    @staticmethod
    def deserialize_rep(       
        buffer,
        iq_config,
        num_sample_rep
        ):

        dc = DataChunk(
            iq_config=iq_config,
            num_sample_rep = num_sample_rep
        )

        data_field_list = []
        data_field_dic = {}
        data_block_list = []
        data_block_list_I = []
        data_block_list_Q = []
        data_block_dic = {}


        for i in range(num_sample_rep):
            if (iq_config == 0b01 or iq_config == 0b10):
                # print block data
                bit_msb_pos = i*14
                data_block_list.append(helper_deserialize(buffer, bit_msb_pos, 14))
            else:
                # print block data
                bit_msb_pos = i*2*14
                data_block_list_I.append(helper_deserialize(buffer, bit_msb_pos, 14))
                bit_msb_pos = (i*2+1)*14
                data_block_list_Q.append(helper_deserialize(buffer, bit_msb_pos, 14))
        
        
        s2_11_converter = DataFormatConverter(signedness = "signed", m = 2, n = 11)
        if(iq_config == 0b01): 
            # s2_11_converter.bin_to_real
            data_block_dic['ReplicaOutI'] = [s2_11_converter.bin_to_real(bin(data_block_list[i])) for i in range(len(data_block_list))]
        elif(iq_config == 0b10): 
            data_block_dic['ReplicaOutQ'] = [s2_11_converter.bin_to_real(bin(data_block_list[i])) for i in range(len(data_block_list))]
        else:
            data_block_dic['ReplicaOutI'] = [s2_11_converter.bin_to_real(bin(data_block_list_I[i])) for i in range(len(data_block_list_I))]
            data_block_dic['ReplicaOutQ'] = [s2_11_converter.bin_to_real(bin(data_block_list_Q[i])) for i in range(len(data_block_list_Q))]

        data_field_dic['data_field'] = data_block_dic

        return data_field_dic



class SF_ECHO_HEADER(recordclass('SF_ECHO_HEADER',[
        "SFSY",
        "SFID",
        "SFLN",
        "operation",
        "with_dpca",
        "use_udcapc",
        "num_burst",
        "num_look",
        "look_angle",
        "squint_angle",
        "rx_gain_set",
        "compression",
        "block_size_mode",
        "baq_seg_mode",
        "word_length_mode",
        "pulse_count",
        "burst_change",
        "rx_beam_flag",
        "rx_polarization",
        "tx_polarization",
        "off_tx_flag",
        "echo_delay_pulses",
        "pri",
        "pulse_width",
        "tx_bandwidth",
        "tx_waveform",
        "tx_initial_phase",
        "tx_beamwidth_el",
        "tx_beamwidth_az",
        "tx_beam_zenith",
        "tx_beam_squint",
        "rx_beamwidth_el",
        "rx_beamwidth_az",
        "rx_beam_zenith",
        "rx_beam_squint",
        "rx_start_time",
        "num_block",
        "decim_filter",
        "decim_factor_m1",
        "tx_output_power",
        "SAD",
        "IGPST",
        "ICNT"
])):
    
    bit_fields = []
    bit_fields += [BitField("SFSY",0,64)]
    bit_fields += [BitField("SFID",64,8)]
    bit_fields += [BitField("SFLN",72,24)]
    bit_fields += [BitField("operation",96,3)]
    bit_fields += [BitField("with_dpca",99,1)]
    bit_fields += [BitField("use_udcapc",100,2)]
    bit_fields += [BitField("num_burst",102,10)]
    bit_fields += [BitField("num_look",112,3)]
    bit_fields += [BitField("look_angle",115,11)]
    bit_fields += [BitField("squint_angle",126,8)]
    bit_fields += [BitField("rx_gain_set",134,8)]
    bit_fields += [BitField("compression",142,2)]
    bit_fields += [BitField("block_size_mode",144,2)]
    bit_fields += [BitField("baq_seg_mode",146,1)]
    bit_fields += [BitField("word_length_mode",147,3)]
    bit_fields += [BitField("pulse_count",152,20)]
    bit_fields += [BitField("burst_change",172,1)]
    bit_fields += [BitField("rx_beam_flag",181,3)]
    bit_fields += [BitField("rx_polarization",184,1)]
    bit_fields += [BitField("tx_polarization",185,1)]
    bit_fields += [BitField("off_tx_flag",186,1)]
    bit_fields += [BitField("echo_delay_pulses",187,6)]
    bit_fields += [BitField("pri",193,18)]
    bit_fields += [BitField("pulse_width",211,15)]
    bit_fields += [BitField("tx_bandwidth",226,11)]
    bit_fields += [BitField("tx_waveform",237,3)]
    bit_fields += [BitField("tx_initial_phase",240,2)]
    bit_fields += [BitField("tx_beamwidth_el",242,3)]
    bit_fields += [BitField("tx_beamwidth_az",245,2)]
    bit_fields += [BitField("tx_beam_zenith",247,12)]
    bit_fields += [BitField("tx_beam_squint",259,10)]
    bit_fields += [BitField("rx_beamwidth_el",269,3)]
    bit_fields += [BitField("rx_beamwidth_az",272,3)]
    bit_fields += [BitField("rx_beam_zenith",275,12)]
    bit_fields += [BitField("rx_beam_squint",287,10)]
    bit_fields += [BitField("rx_start_time",297,18)]
    bit_fields += [BitField("num_block",315,16)]
    bit_fields += [BitField("decim_filter",331,3)]
    bit_fields += [BitField("decim_factor_m1",334,6)]
    bit_fields += [BitField("tx_output_power",340,14)]
    bit_fields += [BitField("SAD",376,128)]
    bit_fields += [BitField("IGPST",504,56)]
    bit_fields += [BitField("ICNT",560,32)]


    def __init__(self, *args, **kwargs):
        recordclass.__init__(self, *args, **kwargs)

    def serialize(self, verbose=False):
        # serialize to 8 bit
        buffer = bytearray(75)
        for bit_field in SF_ECHO_HEADER.bit_fields: 
            helper_serialize(buffer, getattr(self, bit_field.name), bit_field.lsb, bit_field.length)
        return buffer

    @staticmethod
    def deserialize(buffer, verbose=False):
        # deserialize_sf_echo_header
        bit_field_data = dict()
        for bit_field in SF_ECHO_HEADER.bit_fields:
            bit_field_data[bit_field.name] = helper_deserialize(buffer, bit_field.lsb, bit_field.length)
        return SF_ECHO_HEADER(**bit_field_data)
    
    @staticmethod
    def init():
        bit_field_data = dict()
        for bit_field in SF_ECHO_HEADER.bit_fields:
            bit_field_data[bit_field.name] = 0
        return SF_ECHO_HEADER(**bit_field_data)

    @staticmethod
    def randomize():
        bit_field_data = dict()
        for bit_field in SF_ECHO_HEADER.bit_fields:
            bit_field_data[bit_field.name] = random.randint(0,(1<<bit_field.length)-1)
        return SF_ECHO_HEADER(**bit_field_data)
    
    @staticmethod
    def parse(buf):
        header_dic = {}
        for bit_field in SF_ECHO_HEADER.bit_fields:
            if bit_field.name in ("SFSY","SAD","IGPST","ICNT"):
                header_dic[bit_field.name]=hex(getattr(buf, bit_field.name))
            elif bit_field.name in ("SFID"):
                header_dic[bit_field.name]=bin(getattr(buf, bit_field.name))
            else:
                header_dic[bit_field.name]=int(getattr(buf, bit_field.name))
        return header_dic
    
class SF_REPLICA_HEADER(recordclass('SF_REPLICA_HEADER',[
        "SFSY",
        "SFID",
        "SFLN",
        "ReplicaFlag",
        "PulseCount",
        "TxPolarization",
        "NumSample_Rep"
])):
    bit_fields = []
    bit_fields += [BitField("SFSY",0,64)]
    bit_fields += [BitField("SFID",64,8)]
    bit_fields += [BitField("SFLN",72,24)]
    bit_fields += [BitField("ReplicaFlag",96,2)]
    bit_fields += [BitField("PulseCount",98,20)]
    bit_fields += [BitField("TxPolarization",118,1)]
    bit_fields += [BitField("NumSample_Rep",119,17)]

    def __init__(self, *args, **kwargs):
        recordclass.__init__(self, *args, **kwargs)

    def serialize(self, verbose=False):
        # serialize to 8 bit
        buffer = bytearray(18)
        for bit_field in SF_REPLICA_HEADER.bit_fields: 
            helper_serialize(buffer, getattr(self, bit_field.name), bit_field.lsb, bit_field.length)
        return buffer

    @staticmethod
    def deserialize(buffer, verbose=False):
        # deserialize_SF_REPLICA_HEADER
        bit_field_data = dict()
        for bit_field in SF_REPLICA_HEADER.bit_fields:
            bit_field_data[bit_field.name] = helper_deserialize(buffer, bit_field.lsb, bit_field.length)
        return SF_REPLICA_HEADER(**bit_field_data)
    
    @staticmethod
    def init():
        bit_field_data = dict()
        for bit_field in SF_REPLICA_HEADER.bit_fields:
            bit_field_data[bit_field.name] = 0
        return SF_REPLICA_HEADER(**bit_field_data)

    @staticmethod
    def randomize():
        bit_field_data = dict()
        for bit_field in SF_REPLICA_HEADER.bit_fields:
            bit_field_data[bit_field.name] = random.randint(0,(1<<bit_field.length)-1)
        return SF_REPLICA_HEADER(**bit_field_data)
    
    @staticmethod
    def parse(buf):
        header_dic = {}
        for bit_field in SF_REPLICA_HEADER.bit_fields:
            if bit_field.name in ("SFSY"):
                header_dic[bit_field.name]=hex(getattr(buf, bit_field.name))
            elif bit_field.name in ("SFID"):
                header_dic[bit_field.name]=bin(getattr(buf, bit_field.name))
            else:
                header_dic[bit_field.name]=int(getattr(buf, bit_field.name))
        return header_dic



def hexdump(buf):
    for idx,b in enumerate(buf):
        print(f"{b:02x}", end= "")
        if (idx+1)%8 == 0:
            print()
    print()