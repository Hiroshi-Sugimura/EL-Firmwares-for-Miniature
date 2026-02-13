#!/usr/bin/python3
"""!
@file utils.py
@brief ECHONET Lite共通ユーティリティ関数
@author SUGIMURA Hiroshi, Kanagawa Institute of Technology
@date 2023年度
@details copyライブラリを使わずに実装した軽量な深いコピー関数群
         Python 3.4.0 / MicroPython対応
"""

def deepcopy_list(src):
    """!
    @brief list[int]の深いコピーを作成
    @param src (list)
    @return list
    @details copyライブラリを使わずにリストの深いコピーを実現
    """
    return src[:] if src else []

def deepcopy_dict_pdcedt(src):
    """!
    @brief dict[int, PDCEDT]の深いコピーを作成
    @param src (dict)
    @return dict
    @details copyライブラリを使わずに辞書の深いコピーを実現
             PDCEDTのコピーコンストラクタを利用
    """
    if not src:
        return {}
    result = {}
    # 遅延インポートでPDCEDTを取得
    from PDCEDT import PDCEDT
    for key, value in src.items():
        result[key] = PDCEDT(value)
    return result
