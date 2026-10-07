# P7 原生重开失败诊断

2026-10-07，先方案后实现。第二批normal原13raw在reopen_document记UNKNOWN，当前stderr被丢弃、trace只保留RuntimeError，不能证明是桥接构造、系统拒绝、回复错误还是超时。Apple官方sendEventWithOptions:timeout:error:提供NSError及回复；源码保持等待回复、禁止交互，不改为无回复或增加权限。

本次只补诊断，不宣称修复原故障：在既有JXA内部标注identity/build/send/reply阶段，返回严格固定失败信封和可选有界整数系统错误码；不返回异常正文、路径、stderr或凭据。Python使用RuntimeError子类，固定错误消息保持兼容；对子进程启动/超时/非零退出/协议错误作有限分类。handoff原UNKNOWN增加仅此可信异常的白名单诊断，任意其他异常仍只记类型。

错误依旧UNKNOWN、停止、不重发。PID/出生时间/固定路径、1秒原生等待、3秒子进程期限、30raw和重开后新窗口/正文核验不变。禁止重跑原失败或改变冻结002剩余任务版本；新代码先本地反例验证，之后另行确定实机诊断范围，不拿mock或错误码当业务成功。

验证包括全部既有native/reopen测试、各阶段/数值边界/额外字段/恶意消息拒绝、超时无重试与trace脱敏。README/PROGRESS记清仅诊断实现、原错误仍未知和实机未验收。

接口依据：[Apple sendEventWithOptions:timeout:error:](https://developer.apple.com/documentation/foundation/nsappleeventdescriptor/sendevent%28options%3Atimeout%3A%29?language=objc)，同时核对本机SDK Foundation/NSAppleEventDescriptor.h。不据此推断原次错误码。
