#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为「既无繁体也无日文字形」剩下的字做近义替换（用户指定的最后一档）。

挑选原则：
 - 优先挑能和相邻字拼成正统日文词/自然中文词的组合（如 玫瑰->薔薇、蜡烛->蝋燭、
   啰嗦->冗長、伤疤->伤痕、玷污->染汚）。
 - 纯拟声词无可用的汉字，改用假名（与原 ".particles -> kana" 的处理一致）。
每个字给出候选优先级，逐个校验 cp932 可编码后才采用。
"""
import json, os

ROOT = os.path.abspath('.')
MAP = os.path.join(ROOT, '.work', 'glyph_map.json')
ZH_BACKUP = os.path.join(ROOT, '.work', 'zh_backup')


def d(ch):
    try:
        return len(ch.encode('cp932')) == 2
    except Exception:
        return False


g = json.load(open(MAP, encoding='utf-8'))

# 近义替换候选表：源字 -> 按优先级排列的候选
CURATED = {
    '呃': ['え', 'エ'],           # 拟声/迟疑 -> 假名
    '拖': ['延', '引'],           # 拖延 -> 延
    '咚': ['ド'],                 # 咚（心跳声）-> 日文拟声 ド
    '膛': ['腔', '胸'],           # 胸膛 -> 胸腔（正统词）
    '搐': ['痙', '攣'],           # 抽搐 -> 痙（痙攣）
    '焰': ['炎'],                 # 火焰 -> 火炎（正统词）
    '挣': ['逃', '脱'],           # 挣脱 -> 逃脱（通顺）
    '孽': ['業'],                 # 罪孽 -> 罪業（正统词）
    '踢': ['蹴'],                 # 踢 -> 蹴（日文 蹴る）
    '垮': ['崩'],                 # 垮 -> 崩（崩れる）
    '挖': ['嘲', '掘'],           # 挖苦 -> 嘲
    '磕': ['躓', '転'],           # 磕绊 -> 躓（躓く）
    '吞': ['呑'],                 # 吞 -> 呑（呑む）
    '污': ['汚'],                 # 污 -> 汚（日文正字）
    '砰': ['バ'],                 # 砰 -> 日文拟声 バ
    '偷': ['盗'],                 # 偷听 -> 盗（盗み聞き）
    '囔': ['呟', '言'],           # 嘟囔 -> 呟（呟く）
    '撇': ['背', '逸'],           # 把脸撇开 -> 背（背ける）
    '盯': ['凝', '視'],           # 盯着 -> 凝（凝視）
    '噘': ['尖'],                 # 噘嘴 -> 尖（尖らす）
    '嗖': ['ス'],                 # 嗖 -> 日文拟声 ス
    '拽': ['引'],                 # 拽住 -> 引（引く）
    '丢': ['任', '投'],           # 丢给 -> 任（任せる）
    '撂': ['置'],                 # 撂着 -> 置（置く）
    '臊': ['羞', '恥'],           # 害臊 -> 害羞（正统词）
    '趟': ['度', '回'],           # 一趟 -> 一度
    '涉': ['係', '絡'],           # 牵涉 -> 係（関係）
    '绑': ['縛'],                 # 绑 -> 縛（縛る）
    '蹬': ['蹴'],                 # 蹬 -> 蹴
    '憋': ['堪', '耐'],           # 憋着 -> 堪（堪える）
    '瞧': ['見'],                 # 瞧 -> 見（見る）
    '泼': ['溌'],                 # 活泼 -> 活溌（日文正统）
    '俱': ['備', '共'],           # 与生俱来 -> 備（備わる）
    '揭': ['済', '流'],           # 揭过去 -> 済（済ます）
    '蹩': ['拙'],                 # 蹩脚 -> 拙（拙い）
    '囊': ['弱', '駄'],           # 窝囊 -> 弱
    '摔': ['投', '落'],           # 摔落 -> 投（投げる）
    '玷': ['染'],                 # 玷污 -> 染（染める）
    '疤': ['痕'],                 # 伤疤 -> 伤痕（正统词）
    '蹭': ['擦'],                 # 磨蹭 -> 磨擦（正统词）
    '攥': ['握', '掴'],           # 攥住 -> 握住
}

# 需要成对改写，才能落成完整日文词的：源字 -> (伙伴字, 伙伴目标, 自己目标)
PAIRS = {
    '玫': ('瑰', '薇', '薔'),     # 玫瑰 -> 薔薇
    '蜡': ('烛', '燭', '蝋'),     # 蜡烛 -> 蝋燭
    '啰': ('嗦', '長', '冗'),     # 啰嗦 -> 冗長
}

# 窗户：先看「窗」现在落到什么，再决定「户」配什么，避免重复成 窗窓
cur_win = g.get('窗', '窗' if d('窗') else None)
print('窗 当前状态:', repr(cur_win), '(可编码:', d('窗'), ')')
if cur_win == '窓':
    CURATED['户'] = ['辺']        # -> 窓辺（正统词）
else:
    CURATED['户'] = ['窓']        # -> 窗窓 ~ 窗口之意；兜底再窓
    print('  注：窗 未在表中落到 窓，户 取 窓')

applied, failed = [], []
for src, cands in CURATED.items():
    got = None
    for c in cands:
        if d(c):
            got = c
            break
    if got is None:
        failed.append(src)
        continue
    applied.append((src, g.get(src), got))
    g[src] = got

print()
print('=== 成对改写（使整词落成日文词） ===')
for src, (mate, mate_target, own) in PAIRS.items():
    if not d(own):
        print('  跳过 %s（目标 %s 不可编码）' % (src, own)); continue
    if not d(mate_target):
        print('  跳过配对 %s+%s（目标 %s 不可编码）' % (src, mate, mate_target)); continue
    prev_self, prev_mate = g.get(src), g.get(mate)
    g[src] = own
    g[mate] = mate_target
    print('  %s%s: (%s,%s) -> (%s,%s)' %
          (src, mate, prev_self, prev_mate, own, mate_target))

json.dump(g, open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('=== 已采用的近义替换（%d 项） ===' % len(applied))
print('  源 -> 旧值 -> 新值')
for s, o, n in applied:
    print('   %s : %s -> %s' % (s, o, n))
if failed:
    print('候选全部不可编码(仍无解):', failed)

# ---- 复检语料 ----
loc = {}
for f in sorted(os.listdir(ZH_BACKUP)):
    if f.endswith('.json'):
        for v in json.load(open(os.path.join(ZH_BACKUP, f), encoding='utf-8')).values():
            for ch in v:
                if '\u4e00' <= ch <= '\u9fff' and not d(ch):
                    loc[ch] = loc.get(ch, 0) + 1
still = [c for c in loc if not d(g.get(c, ''))]
print()
print('=== 复检 ===')
print('语料需映射字:', len(loc))
print('仍无解(会变成中点・):', len(still), ''.join(sorted(still)))
print('表中条目数:', len(g))
