"""
开盘啦首轮验证清单。

【APP-SPECIFIC 边界 - 这是开盘啦特有的验证清单】
- 这个文件是开盘啦特有的首轮验证清单
- 不应被视为通用的多 app checklist
- build_first_round_checklist() 返回开盘啦的验证清单
- 标题硬编码为 "开盘啦首轮验证清单"
- items 中的验证项是基于开盘啦特有的 UI 和功能设计的

【禁止跨 app 复用的内容】
- 整个清单的逻辑和结构
- 标题和具体验证项的内容
- 对开盘啦特有的 UI 和功能的假设
- risks 和 recap_template 的具体内容

如果其他 app（如开盘红）需要类似 checklist：
1. 应建立独立的 checklist.py
2. 使用自己的标题和验证项
3. 基于 自己的 UI 和功能设计验证项
4. 不应复用此文件的任何具体内容

【与多 app bridge 的关系】
- 此文件是开盘啦特有的辅助工具
- 不在多 app bridge 的通用路径上
- 只用于开盘啦的迁移和验证过程
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ChecklistItem:
    """单个验证项。"""

    step: str
    purpose: str
    evidence: str
    done_when: str
    fallback: str


@dataclass(slots=True)
class ValidationChecklist:
    """首轮验证清单。"""

    title: str
    items: list[ChecklistItem] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recap_template: list[str] = field(default_factory=list)


def build_first_round_checklist() -> ValidationChecklist:
    """构建开盘啦第一轮验证清单。"""

    return ValidationChecklist(
        title="开盘啦首轮验证清单",
        items=[
            ChecklistItem(
                step="环境就绪",
                purpose="确认 Mac mini 能作为执行机，手机、ADB、mitmproxy、Node 均可用。",
                evidence="adb devices、mitmdump 启动、uiautomator2 连通、Node 可执行。",
                done_when="手机连通、代理监听、基础命令全部可用。",
                fallback="先修环境，不进入 App 适配。",
            ),
            ChecklistItem(
                step="App 画像",
                purpose="确认包名、启动页、首页形态、关键页面类型。",
                evidence="真机截图、页面文字、activity、菜单结构。",
                done_when="能描述首页和至少一个目标页面的进入/返回路径。",
                fallback="先只记录页面形态，不写控制逻辑。",
            ),
            ChecklistItem(
                step="代理抓包",
                purpose="确认是否能看到真实请求和可解析响应。",
                evidence="mitmproxy 日志、抓到的 JSON、原始响应样本。",
                done_when="至少抓到一类稳定接口样本。",
                fallback="如果证书或加密阻断，先停在问题定位阶段。",
            ),
            ChecklistItem(
                step="页面控制",
                purpose="确认 uiautomator2 是否能稳定进入/返回目标页面。",
                evidence="点击、滑动、返回、页面状态切换记录。",
                done_when="能从首页进入目标页并安全返回。",
                fallback="如果页面不稳定，先缩小目标页范围。",
            ),
            ChecklistItem(
                step="最小闭环",
                purpose="从启动 App 到抓到一小批数据并入库。",
                evidence="SQLite 新记录、导出文件、原始响应留档。",
                done_when="闭环可重复执行。",
                fallback="只保留单页单接口，别扩展更多功能。",
            ),
        ],
        risks=[
            "不要把小红书的 host/path/package 直接迁移到开盘啦。",
            "不要在没有抓包证据前写死 parser。",
            "不要先做全量重构，先做最小闭环。",
            "不要在 Windows 上把最终链路当成结论。",
            "不要忘记代理清理，避免手机看起来断网。",
        ],
        recap_template=[
            "日期",
            "分支",
            "Mac mini 状态",
            "手机状态",
            "App 版本",
            "抓包结果",
            "UI 结果",
            "失败点",
            "下一步动作",
        ],
    )

