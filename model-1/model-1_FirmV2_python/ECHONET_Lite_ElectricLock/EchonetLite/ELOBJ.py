#!/usr/bin/python3
"""!
@file ELOBJ.py
@brief ECHONET Liteオブジェクト部分
@author SUGIMURA Hiroshi, Kanagawa Institute of Technology
@date 2023年度
@details PDCEDTをEPCと結びつけて管理することを主とする
"""
if __name__ == '__main__':
    from EchonetLite.utils import deepcopy_list, deepcopy_dict_pdcedt
    from EchonetLite.PDCEDT import PDCEDT
elif __name__ == 'EchonetLite.ELOBJ':
    from .utils import deepcopy_list, deepcopy_dict_pdcedt
    from .PDCEDT import PDCEDT
else:
    from utils import deepcopy_list, deepcopy_dict_pdcedt
    from PDCEDT import PDCEDT


class ELOBJ():
    """!
    @brief ELOBJクラス
    @details PDCEDTをEPCと結びつけて管理することを主とする
    """

    def __init__(self, other = None):
        """!
        @brief コンストラクタ
        @param other (ELOBJ) = None
        """
        self.pdcedts = {}
        self.inf_property_map_raw = [] # 9d
        self.set_property_map_raw = [] # 9e
        self.get_property_map_raw = [] # 9f
        # コピーコンストラクタの実現
        if other is None:
            pass
        elif isinstance(other, ELOBJ):
            self.pdcedts = deepcopy_dict_pdcedt(other.pdcedts)
            self.inf_property_map_raw = deepcopy_list(other.inf_property_map_raw)
            self.set_property_map_raw = deepcopy_list(other.set_property_map_raw)
            self.get_property_map_raw = deepcopy_list(other.get_property_map_raw)
        else:
            raise TypeError("ELOBJ: other must be None or ELOBJ, got {}".format(type(other).__name__))

    def __del__(self):
        """!
        @brief デストラクタ
        """
        # print("__del__")
        return

    def __eq__(self, other):
        """!
        @brief 等価演算子 ELOBJ == ELOBJ の実現
        @param paramはother（左辺）
        @return boolean
        """
        if not isinstance(other, ELOBJ):
            return NotImplemented

        return (self.pdcedts == other.pdcedts and
                self.inf_property_map_raw == other.inf_property_map_raw and
                self.set_property_map_raw == other.set_property_map_raw and
                self.get_property_map_raw == other.get_property_map_raw)

    def __getitem__(self, epc):
        """!
        @brief  配列[]インタフェースを提供する。特にrvalue として
        @param  epc (int)
        @return PDCEDT | None
        """
        # print('__getitem__ epc:', epc)
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.__getitem__: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.__getitem__: epc must be 0x80-0xff, got {}".format(hex(epc)))

        if epc in self.pdcedts:
            # print('exist')
            return self.pdcedts[epc]
        else:
            return None

    def __setitem__(self, epc, pdcedt):
        """!
        @brief 配列[]インタフェースを提供する。特にlvalueとして
        @param pdcedt (PDCEDT)
        @return PDCEDT
        @note 新規EPCに対するアクセスはエラーとなる。新規EPCはSetPDCEDTまたはSetEDTを使うこと
        """
        print('__setitem__')
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.__setitem__: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.__setitem__: epc must be 0x80-0xff, got {}".format(hex(epc)))
        if not isinstance(pdcedt, PDCEDT):
            raise TypeError("ELOBJ.__setitem__: pdcedt must be PDCEDT, got {}".format(type(pdcedt).__name__))

        self.pdcedts[epc] = pdcedt
        return self.pdcedts[epc]

    def GetPDCEDT(self, epc):
        """!
        @brief EPCに対応するPDCEDTを取得する
        @param epc int
        @return PDCEDT | None
        """
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.GetPDCEDT: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.GetPDCEDT: epc must be 0x80-0xff, got {}".format(hex(epc)))

        if epc in self.pdcedts:
            # print('exist')
            return self.pdcedts[epc]
        else:
            return None

    def SetPDCEDT(self, epc, pdcedt):
        """!
        @brief EPCに対応するPDCEDTをセットする
        @param epc int
        @param pdcedt (PDCEDT | list[int])
        @return PDCEDT
        """
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.SetPDCEDT: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.SetPDCEDT: epc must be 0x80-0xff, got {}".format(hex(epc)))

        if isinstance(pdcedt, PDCEDT):
            self.pdcedts[epc] = pdcedt
        elif isinstance(pdcedt, list):
            self.pdcedts[epc] = PDCEDT(pdcedt)
        else:
            raise TypeError("ELOBJ.SetPDCEDT: pdcedt must be PDCEDT or list, got {}".format(type(pdcedt).__name__))

        return self.pdcedts[epc]

    def SetEDT(self, epc, edt):
        """!
        @brief EPCに対してEDTをセットする。この際、PDCは自動計算する
        @param epd int
        @param edt list[int]
        @return PDCEDT
        """
        # print('ELOBJ.SetEDT epc:', epc, 'edt', edt)
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.SetEDT: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.SetEDT: epc must be 0x80-0xff, got {}".format(hex(epc)))
        if not isinstance(edt, list):
            raise TypeError("ELOBJ.SetEDT: edt must be list, got {}".format(type(edt).__name__))

        self.pdcedts[epc] = PDCEDT()
        self.pdcedts[epc].setEDT(edt)
        return self.pdcedts[epc]

    def GetMyPropertyMap(self, epc):
        """!
        @brief 自身のPropertyMapを取得する
        @param epc int 0x9d=INF, 0x9e=SET, 0x9f=GET
        @return list[int] | None
        """
        #print("GetMyPropertyMap")
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.GetMyPropertyMap: epc must be int, got {}".format(type(epc).__name__))

        if epc == 0x9d:
            return self.inf_property_map_raw
        elif epc == 0x9e:
            return self.set_property_map_raw
        elif epc == 0x9f:
            return self.get_property_map_raw
        else:
            raise ValueError("ELOBJ.GetMyPropertyMap: epc must be 0x9d, 0x9e or 0x9f, got {}".format(hex(epc)))

    def SetMyPropertyMap(self, epc, epcList):
        """!
        @brief 自身のPropertyMapを設定する
        @param epc int 0x9d=INF, 0x9e=SET, 0x9f=GET
        @param epcList list[int]
        @return PDCEDT | None
        """
        # print("SetMyPropertyMap")
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.SetMyPropertyMap: epc must be int, got {}".format(type(epc).__name__))
        if not isinstance(epcList, list):
            raise TypeError("ELOBJ.SetMyPropertyMap: epcList must be list, got {}".format(type(epcList).__name__))

        # epcListの各要素を検証
        for i, val in enumerate(epcList):
            if not isinstance(val, int):
                raise TypeError("ELOBJ.SetMyPropertyMap: epcList[{}] must be int, got {}".format(i, type(val).__name__))
            if val < 0x80 or val > 0xff:
                raise ValueError("ELOBJ.SetMyPropertyMap: epcList[{}] must be 0x80-0xff, got {}".format(i, hex(val)))

        if epc == 0x9d:
            self.inf_property_map_raw = epcList
        elif epc == 0x9e:
            self.set_property_map_raw = epcList
        elif epc == 0x9f:
            self.get_property_map_raw = epcList
        else:
            raise ValueError("ELOBJ.SetMyPropertyMap: epc must be 0x9d, 0x9e or 0x9f, got {}".format(hex(epc)))

        n = len(epcList)
        if n < 16: # format 1
            pdcedt = PDCEDT()
            epcList.insert(0, n)
            pdcedt.setEDT(epcList)
            self.pdcedts[epc] = pdcedt
        else: # format 2
            temp_edt = [0] * 17
            temp_edt[0] = n
            for v in epcList:
                i = (v & 0x0f) + 1
                flag = 0x01 << ((v >> 4) -8)
                temp_edt[i] += flag
            pdcedt = PDCEDT()
            pdcedt.setEDT(temp_edt)
            self.pdcedts[epc] = pdcedt
        return self.pdcedts[epc]

    def hasInfProperty(self, epc):
        """!
        @brief 自身のINFプロパティか調べる
        @param epc int
        @return bool
        """
        # print("hasInfProperty")
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.hasInfProperty: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.hasInfProperty: epc must be 0x80-0xff, got {}".format(hex(epc)))
        return epc in self.inf_property_map_raw

    def hasSetProperty(self, epc):
        """!
        @brief 自身のSETプロパティか調べる
        @param epc int
        @return bool
        """
        # print("hasSetProperty")
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.hasSetProperty: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.hasSetProperty: epc must be 0x80-0xff, got {}".format(hex(epc)))
        return epc in self.set_property_map_raw

    def hasGetProperty(self, epc):
        """!
        @brief 自身のGETプロパティか調べる
        @param epc int
        @return bool
        """
        # print("hasGetProperty")
        if not isinstance(epc, int):
            raise TypeError("ELOBJ.hasGetProperty: epc must be int, got {}".format(type(epc).__name__))
        if epc < 0x80 or epc > 0xff:
            raise ValueError("ELOBJ.hasGetProperty: epc must be 0x80-0xff, got {}".format(hex(epc)))
        return epc in self.get_property_map_raw

    def println(self):
        """!
        @brief 格納しているEPC、PDCEDTをすべて表示する
        """
        # print("===== ELOBJ.print()")
        for key in self.pdcedts:
            #print("EPC:", format(key,'02x'), ",", self.pdcedts[key].printString() )
            print("EPC:", '{:02X}'.format(key), ",", self.pdcedts[key].printString() )


if __name__ == '__main__':
    print("===== EL_ELOBJ.py 単体テスト")
    # 1
    print("test1")
    test1 = ELOBJ()
    test1.println()
    # 2
    print("test2")
    test2 = ELOBJ()
    test2.SetPDCEDT( 0x80, PDCEDT([0x01, 0x30]) )
    test2.println()
    print("test2 [80]")
    p = test2[0x80]
    """
    # 以下、問題ないけどライブラリとしてWarningがうるさいのでブロックコメント
    if p != None:
        p.println()
    print("test2 [81]")
    p = test2[0x81]
    if p != None:
        p.println()
    print("test2 [82]")
    test2.SetEDT(0x82, [0x31])
    p = test2[0x82]
    if p != None:
        p.println()
    test2[0x82].setEDT([0x31, 0x32])
    p = test2[0x82]
    if p != None:
        p.println()
    """
    # 3
    print("test3")
    test3 = ELOBJ()
    test3.SetPDCEDT( 0x81, [0x01, 0x31] )
    test3.SetPDCEDT( 0x82, [0x01, 0x32] )
    test3.println()
    print("test4")
    test1 = test3
    test1.println()
    test3.SetEDT(0x82, [0x33])
    test3.SetEDT(0x83, [0x33])
    test3.println()
    print("test5")
    test3.SetMyPropertyMap(0x9d, [0x80, 0x81, 0x82, 0x83, 0x84, 0x90, 0x91, 0x92, 0x93, 0x94, 0xa1, 0xa2, 0xb1, 0xb2])
    test3.println()
    test3.SetMyPropertyMap(0x9e, [0x80, 0x81, 0x82, 0x83, 0x84, 0x90, 0x91, 0x92, 0x93, 0x94, 0xa1, 0xa2, 0xb1, 0xb2,0xb3])
    test3.println()
    test3.SetMyPropertyMap(0x9f, [0x80, 0x81, 0x82, 0x83, 0x84, 0x90, 0x91, 0x92, 0x93, 0x94, 0xa1, 0xa2, 0xb1, 0xb2,0xb3,0xb4])
    test3.println()
    print( test1 == test3 )
    print( test3.hasSetProperty(0x90) )
    print( test3.hasGetProperty(0x95) )
