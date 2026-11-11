import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  MarkAreaComponent,
  GraphicComponent,
  AxisPointerComponent,
  ToolboxComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import { useUI } from "@/lib/store";

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  MarkAreaComponent,
  GraphicComponent,
  AxisPointerComponent,
  ToolboxComponent,
  CanvasRenderer,
]);

export { echarts };

export const AXIS_TEXT = "#8B97B1";
export const SPLIT = "rgba(255,255,255,0.06)";

export const tooltipBase = {
  backgroundColor: "rgba(13,20,36,0.94)",
  borderColor: "rgba(255,255,255,0.12)",
  borderWidth: 1,
  padding: [10, 14],
  textStyle: { color: "#E2E8F0", fontFamily: "Inter", fontSize: 13 },
  extraCssText: "border-radius:12px;box-shadow:0 20px 50px -20px rgba(0,0,0,.8);backdrop-filter:blur(12px);",
};

export const axisBase = {
  axisLine: { lineStyle: { color: "rgba(255,255,255,0.14)" } },
  axisTick: { show: false },
  axisLabel: { color: AXIS_TEXT, fontFamily: "JetBrains Mono", fontSize: 11 },
  splitLine: { lineStyle: { color: SPLIT } },
  nameTextStyle: { color: AXIS_TEXT, fontFamily: "Inter", fontSize: 12 },
};

export function Chart({
  option,
  height = 360,
  notMerge = false,
  className,
}: {
  option: EChartsOption;
  height?: number | string;
  notMerge?: boolean;
  className?: string;
}) {
  const presenter = useUI((s) => s.presenter);
  const merged: EChartsOption = {
    backgroundColor: "transparent",
    textStyle: { fontFamily: "Inter", color: "#CBD5E1", fontSize: presenter ? 14 : 12 },
    animationDuration: 1100,
    animationEasing: "cubicOut",
    animationDurationUpdate: 600,
    ...option,
  };
  return (
    <ReactEChartsCore
      echarts={echarts}
      option={merged}
      notMerge={notMerge}
      lazyUpdate
      style={{ height, width: "100%" }}
      className={className}
      opts={{ renderer: "canvas" }}
    />
  );
}
