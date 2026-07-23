"""Append longer, more meaningful phrases to too-short assessment_prompts."""
import sys
sys.path.insert(0, '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/src/pipeline/v33_art')
import generate

# Each suffix needs to be long enough to push total ≥ 150
# (cid, full_new_last_question)  -- replaces the entire last question
# We use the last "?" and replace the LAST question with a longer version.

# Strategy: replace the LAST question (after the last "\n") with a longer one.
NEW_LAST_Q = {
    "ART_A1_01": "听到一段慢歌突然变快,{{name}}能不能立刻说出「音乐变快了」并解释为什么身体也跟着加快,试 2 遍?",
    "ART_A2_01": "看到梵高《向日葵》里有 5 种黄色,{{name}}能不能猜出至少有 2 种是红+黄调出来的不同深浅,自己说 1 句?",
    "ART_A2_04": "用废旧纸板和胶水搭一个 10 厘米高的小房子,{{name}}能不能让房子立起来不倒、墙面不歪,试试看?",
    "ART_A2_06": "画完一幅水墨竹子,{{name}}能不能指出画面里哪几笔用了中锋、哪几笔用了侧锋,2 处都要说出?",
    "ART_A2_07": "一个水杯,{{name}}能不能指出 3 个「要握着舒服」的设计细节 (杯身弧度/杯把宽度/防滑底),具体说?",
    "ART_A3_01": "闭眼听 1 分钟音乐,{{name}}能不能用手臂画出音乐在「高」还是在「低」的位置,2 个都要画?",
    "ART_A3_02": "跳完一段傣族舞,{{name}}能不能说出「为什么手要一直在身体一侧弯着」 (三道弯),用 1 句说清?",
    "ART_A3_03": "跳给同学看之前,{{name}}能不能自己说出「这段舞想表达什么」一句话来介绍,1 句不超 20 字?",
    "ART_A4_01": "表演完一段,{{name}}能不能说出自己「最满意」和「最想改」各 1 个动作,2 个都要说?",
    "ART_A5_01": "看完一段默片 (无对白),{{name}}能不能用 3 句话讲清导演想说什么,3 句都要有?",
    "ART_A5_02": "拍完上传前,{{name}}能不能自己先看一遍,指出 1 个想改的地方 (光线/声音/节奏),并说明为什么?",
    "ART_A6_01": "听到一首喜欢的歌,{{name}}能不能说出「它让我想到生活中的什么场景」,用 1 句 15 字内说清?",
    "ART_A6_02": "看 3 幅来自不同国家的画,{{name}}能不能猜出哪幅来自中国、哪幅来自日本、哪幅来自意大利,1 个不错?",
    "ART_G12_MU_01": "学小鸟叫「啾啾」和火车「呜——」,{{name}}能不能自己用嘴巴模仿 3 种自然声音,2 种像?",
    "ART_G12_MU_02": "听 2 遍同一首歌,{{name}}能不能说出第 2 遍和第 1 遍「哪里一样、哪里不一样」,2 处都说?",
    "ART_G12_MU_04": "听《粉刷匠》一遍,{{name}}能不能在 1 分钟内把听到的 3 个「最好听」的部分哼出来,1 个不出?",
    "ART_G12_MU_05": "全班一起站直唱《上学歌》,{{name}}能不能保持 1 分钟不塌腰、不乱动,唱完再说 1 句感受?",
    "ART_G12_MU_06": "唱歌词「小燕子,穿花衣」,{{name}}能不能把「燕」「穿」「衣」3 个字都念圆,不让音「糊」在一起?",
    "ART_G12_MU_07": "边跳边唱《小星星》第 1 句,{{name}}能不能在唱完后还有气说话,不喘,自己说 1 句?",
    "ART_G12_MU_08": "蒙眼听 3 种乐器 (沙锤/铃鼓/三角铁),{{name}}能不能准确听出哪个是沙锤的声音,3 个对 2 个?",
    "ART_G12_MU_09": "看老师敲 3 下,{{name}}能不能用铃鼓「拍-拍-晃」一模一样地重复一遍,1 遍不差?",
    "ART_G12_MU_10": "按 3/4 拍的《生日歌》,{{name}}能不能在每小节第 1 拍敲三角铁「叮」一次,3 拍对 3 敲?",
    "ART_G12_MU_11": "自己排出 2 小节节奏 (一拍 1 个动作),{{name}}能不能让同桌跟着重复 1 遍,同桌跟得上?",
    "ART_G12_MU_12": "全班一起跳「动物圆圈舞」,{{name}}能不能听到「大象」就慢、听到「兔子」就快,不乱?",
    "ART_G12_AR_01": "画完一棵小树,{{name}}能不能自己检查「树干的粗细是不是上下一样」,并改 1 处?",
    "ART_G12_AR_02": "看到 1 块橙色布和 1 块紫色布,{{name}}能不能猜出哪块「像太阳」哪块「像葡萄」,2 个对 1 个?",
    "ART_G12_AR_03": "贺卡用红色还是粉色?{{name}}能不能说出选这个颜色的「1 个理由」,1 句不超 15 字?",
    "ART_G12_AR_05": "胶水涂太多时,{{name}}能不能用纸巾马上擦掉,不让画面变皱,试试 1 张?",
    "ART_G12_DA_01": "听到「蹲-起-立」口令,{{name}}能不能用「正步-小八字-大八字」3 种脚位依次做出来,3 个不乱?",
    "ART_G12_DA_02": "跳给同桌看一遍,{{name}}能不能自己说出「哪个动作最容易忘」,并自己练 1 次?",
    "ART_G12_DR_01": "玩「传表情」游戏,{{name}}能不能用「皱眉-笑-惊讶」3 个表情依次传给下一个人,不笑场?",
    "ART_G12_DR_02": "演完一段,{{name}}能不能说出「自己最满意」的 1 个动作和「下次想改」的 1 个动作,2 个都说?",
    "ART_G12_FI_01": "比较 2 部动画片 (中国/外国),{{name}}能不能说出 1 处「颜色或人物」不一样的地方,具体说?",
    "ART_G34_MU_01": "齐唱完一段 16 拍,{{name}}能不能在最后一个音「同时收住」,不出现拖音,和同学一起?",
    "ART_G34_MU_02": "老师点评后,{{name}}能不能用 1 句话说出「为什么《茉莉花》不能唱得像进行曲」,1 句不超 25 字?",
    "ART_G34_MU_04": "吹完一段,{{name}}能不能自己说「指法最容易按错」的是哪 1 个孔,3 个说 1 个?",
    "ART_G34_MU_06": "全班一起边唱边做动作,{{name}}能不能「自己的动作和歌声同起同落」,不出现早一拍?",
    "ART_G34_AR_01": "画完一棵墨竹,{{name}}能不能指出画面里「哪一笔是写意、不是工笔」 (一笔成形 vs 一笔一描)?",
    "ART_G34_AR_02": "两张湿纸一张马上画、一张等 5 分钟画,{{name}}能不能看出「干画法」和「湿画法」效果不一样?",
    "ART_G34_AR_05": "烧制前,{{name}}能不能自己检查「碗底是不是平」,让碗能稳稳立在桌上,自己看 1 次?",
    "ART_G34_AR_06": "剪完 1 张雪花,{{name}}能不能自己把雪花展开、对折痕检查「是不是对称」,1 眼看?",
    "ART_G34_AR_07": "编完一块 10×10 cm 的杯垫,{{name}}能不能保证 4 条边都「平整」,没有松紧不一样的地方?",
    "ART_G34_DA_01": "跳给全班看时,{{name}}能不能保证 4 个人的动作「整齐一致」,而不是各跳各的?",
    "ART_G56_MU_01": "听完自己唱的录音,{{name}}能不能指出「1 个最想改」的地方 (太快/太慢/太硬/太软),具体说?",
    "ART_G56_MU_02": "同一首歌的 2 句,1 句用连音、1 句用顿音,{{name}}能不能让 2 句听起来「明显不一样」?",
    "ART_G56_MU_03": "听完一首曲子,{{name}}能不能用「快/慢/中速」+「开心/忧伤/激昂」2 个标签准确描述,2 个都对?",
    "ART_G56_AR_01": "画完 1 幅水墨兰草,{{name}}能不能指出画面里「用了哪 3 种墨色」 (浓/淡/干),3 个说 1 个?",
    "ART_G56_AR_02": "画完球体,{{name}}能不能指出画面里「最亮」「最暗」「中间灰」3 个层次都画出来了?",
    "ART_G56_AR_03": "检查封面时,{{name}}能不能「闭眼 1 秒再睁开」,第一眼看到的是「图」还是「字」,说 1 句?",
    "ART_G56_AR_04": "给同学看标志,{{name}}能不能在 3 秒内说出「这代表什么」一句话,而不是需要解释?",
}


def fix():
    fixed = 0
    skipped = []
    for cid, new_last in NEW_LAST_Q.items():
        ass = generate.GENERATED[cid]["assessment_prompt"]
        old_len = len(ass)
        # Replace the last question (after the last "\n")
        idx = ass.rfind("\n")
        if idx < 0:
            skipped.append((cid, "no newline"))
            continue
        prefix = ass[:idx+1]  # keep the "\n"
        ass_new = prefix + new_last
        new_len = len(ass_new)
        if 150 <= new_len <= 220:
            # Verify {{name}} count
            nc = ass_new.count("{{name}}")
            if nc != 3:
                skipped.append((cid, f"name count {nc}"))
                print(f"  ✗ {cid} name count {nc}")
                continue
            generate.GENERATED[cid]["assessment_prompt"] = ass_new
            fixed += 1
            print(f"  ✓ {cid} ass {old_len}→{new_len}")
        else:
            skipped.append((cid, new_len))
            print(f"  ✗ {cid} would be {new_len}")
    return fixed, skipped


if __name__ == "__main__":
    n, skip = fix()
    print(f"\nFixed {n} entries, skipped {len(skip)}")
    for cid, l in skip:
        print(f"  skipped {cid}: {l}")
