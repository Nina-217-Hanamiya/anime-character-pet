# anime-character-pet

从联网找到的动漫角色原素材制作或修复小人动画和 ChatGPT Pets 的 Codex skill。

默认保留角色原外观，使用原骨骼或原图拆层制作简化动作，不使用 AI 重绘。流程包括素材来源与外观核对、双眼比例检查、实际骨骼约束定位、眨眼/表情和动作切换检查，以及 Pets 的校验与更新。

## 使用

将本仓库放到 Codex 的 `skills/anime-character-pet` 目录。例如：

```sh
git clone https://github.com/Nina-217-Hanamiya/anime-character-pet.git ~/.codex/skills/anime-character-pet
```

调用示例：

> 使用 $anime-character-pet，联网寻找这个角色的原素材，制作 pet 并检查眼睛定位、表情和动作切换。

[SKILL.md](SKILL.md) 是技能入口；`references/` 为分支流程，`scripts/` 为固定眼睛锚点诊断和已保留精灵图行的像素比较。

诊断脚本需要 Python 3；精灵图比较脚本还需要 Pillow。平台正式质量检查和创建/更新需要可用的 Pets 插件。诊断脚本不替代视觉检查或应用内播放验收。

仓库包含技能说明与检查脚本，不包含角色素材、账号宠物记录或临时上传凭据。
