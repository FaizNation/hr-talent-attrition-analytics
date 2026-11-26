import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ModelRecord } from '../types'
import type { BarRow } from '../utils/chartData'
import { formatPct, HAPPINESS_LABELS, LABEL_COLORS } from '../utils/format'

const tooltipStyle = {
  border: '1px solid var(--rule)',
  borderRadius: 2,
  background: 'var(--paper-solid)',
  color: 'var(--ink)',
  fontFamily: 'var(--mono)',
  fontSize: 12,
}

interface DonutProps {
  data: { name: string; value: number; color: string }[]
  centerValue: string
  centerLabel: string
}

export function Donut({ data, centerValue, centerLabel }: DonutProps) {
  return (
    <div className="donut">
      <div className="donut-canvas">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="66%"
              outerRadius="90%"
              paddingAngle={3}
              stroke="none"
            >
              {data.map((slice) => (
                <Cell key={slice.name} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatPct(Number(value))}
              contentStyle={tooltipStyle}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center" aria-hidden="true">
          <strong>{centerValue}</strong>
          <span>{centerLabel}</span>
        </div>
      </div>
      <ul className="chart-legend">
        {data.map((slice) => (
          <li key={slice.name}>
            <span className="legend-dot" style={{ background: slice.color }} />
            <span>{slice.name}</span>
            <b>{formatPct(slice.value)}</b>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function StackedBars({ data }: { data: BarRow[] }) {
  return (
    <div className="stacked-canvas">
      <div className="chart-area">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke="var(--rule)" />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(value: number) => `${value}%`}
            tick={{ fill: 'var(--muted)', fontSize: 11, fontFamily: 'var(--mono)' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={118}
            tick={{ fill: 'var(--ink)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip formatter={(value) => formatPct(Number(value))} contentStyle={tooltipStyle} />
          {HAPPINESS_LABELS.map((label) => (
            <Bar key={label} dataKey={label} stackId="share" fill={LABEL_COLORS[label]} maxBarSize={22} />
          ))}
        </BarChart>
      </ResponsiveContainer>
      </div>
      <ul className="chart-legend inline">
        {HAPPINESS_LABELS.map((label) => (
          <li key={label}>
            <span className="legend-dot" style={{ background: LABEL_COLORS[label] }} />
            {label}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ModelBars({ models }: { models: ModelRecord[] }) {
  const data = models.map((model) => ({
    name: model.Model,
    Accuracy: model['Accuracy (%)'],
    F1: model['F1_Macro (%)'],
  }))

  return (
    <div className="stacked-canvas">
      <div className="chart-area">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--rule)" />
          <XAxis
            dataKey="name"
            tick={{ fill: 'var(--ink)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval={0}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(value: number) => `${value}%`}
            tick={{ fill: 'var(--muted)', fontSize: 11, fontFamily: 'var(--mono)' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip formatter={(value) => formatPct(Number(value))} contentStyle={tooltipStyle} />
          <Bar dataKey="Accuracy" fill="var(--accent)" maxBarSize={34} />
          <Bar dataKey="F1" fill="var(--teal)" maxBarSize={34} />
        </BarChart>
      </ResponsiveContainer>
      </div>
      <ul className="chart-legend inline">
        <li><span className="legend-dot" style={{ background: 'var(--accent)' }} />Accuracy</li>
        <li><span className="legend-dot" style={{ background: 'var(--teal)' }} />F1-Macro</li>
      </ul>
    </div>
  )
}

export function HeatmapTable({ matrix }: { matrix: Record<string, Record<string, number>> }) {
  const rows = Object.keys(matrix)
  const columns = [...new Set(rows.flatMap((row) => Object.keys(matrix[row])))]

  return (
    <div>
      <div className="heatmap-scroll">
        <table className="heatmap">
          <thead>
            <tr>
              <th scope="col">Gaji × Pengalaman</th>
              {columns.map((column) => (
                <th scope="col" key={column}>
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row}>
                <th scope="row">{row}</th>
                {columns.map((column) => {
                  const value = matrix[row][column] ?? 0
                  const alpha = Math.min(0.92, Math.max(0.07, value / 100))
                  return (
                    <td
                      key={column}
                      title={formatPct(value)}
                      style={{
                        background: `rgba(14, 122, 107, ${alpha})`,
                        color: value > 55 ? '#ffffff' : 'var(--ink)',
                      }}
                    >
                      {formatPct(value)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="heatmap-scale" aria-hidden="true">
        <span>0%</span>
        <i />
        <span>100%</span>
      </div>
    </div>
  )
}
