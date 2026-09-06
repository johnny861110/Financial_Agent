// Hand-rolled SVG charts. No charting dependency on purpose: this build runs on
// a ~270 KB/s link, and the whole app is 200KB -- recharts alone would be more
// than double that. SVG also means every value on screen is a DOM node a test
// can assert on, rather than pixels in a canvas.
//
// Every chart takes values that are already computed by the backend. Nothing
// here derives a financial figure; a chart that computed its own numbers would
// be a second source of truth for values the API is authoritative for.

const PALETTE = ['#4f7cff', '#28b48c', '#f0a336', '#e05c5c', '#8b6cf0', '#3aa8c1'];

export function nice(max: number): number {
  if (max <= 0) return 1;
  const pow = 10 ** Math.floor(Math.log10(max));
  return [1, 2, 2.5, 5, 10].map(m => m * pow).find(step => step >= max) ?? 10 * pow;
}

const fmt = (v: number, unit: string) =>
  unit === '%' ? `${v.toFixed(2)}%` : v.toLocaleString('en-US', { maximumFractionDigits: 0 });

/** Horizontal bars. Used where the categories are named and few (margins, returns). */
export function BarChart({ title, data, unit = '%' }: {
  title: string; data: Array<[string, number | null]>; unit?: string;
}) {
  const usable = data.filter(([, v]) => typeof v === 'number' && Number.isFinite(v)) as Array<[string, number]>;
  if (!usable.length) return <ChartEmpty title={title} />;

  // A negative value must not render as a bar growing the same way a positive
  // one does: cash-flow and margin figures are legitimately negative.
  const min = Math.min(0, ...usable.map(([, v]) => v));
  const max = Math.max(0, ...usable.map(([, v]) => v));
  const span = max - min || 1;
  const zero = (-min / span) * 100;

  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <div className="bars">
        {usable.map(([label, value], i) => {
          const width = (Math.abs(value) / span) * 100;
          const left = value >= 0 ? zero : zero - width;
          return (
            <div className="bar-row" key={label}>
              <span className="bar-label">{label}</span>
              <div className="bar-track">
                <span className="bar-zero" style={{ left: `${zero}%` }} />
                <span
                  className="bar-fill"
                  style={{ left: `${left}%`, width: `${width}%`, background: PALETTE[i % PALETTE.length] }}
                />
              </div>
              <span className="bar-value">{fmt(value, unit)}</span>
            </div>
          );
        })}
      </div>
    </figure>
  );
}

/** Donut for a two-or-more part composition that sums to a whole (capital structure). */
export function Donut({ title, data }: { title: string; data: Array<[string, number | null]> }) {
  const usable = data.filter(([, v]) => typeof v === 'number' && v! > 0) as Array<[string, number]>;
  const total = usable.reduce((a, [, v]) => a + v, 0);
  if (!usable.length || total <= 0) return <ChartEmpty title={title} />;

  const R = 60, C = 2 * Math.PI * R;
  let offset = 0;

  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <div className="donut-wrap">
        <svg viewBox="0 0 160 160" className="donut" role="img" aria-label={title}>
          {usable.map(([label, value], i) => {
            const len = (value / total) * C;
            const dash = <circle
              key={label} cx="80" cy="80" r={R} fill="none"
              stroke={PALETTE[i % PALETTE.length]} strokeWidth="26"
              strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset}
              transform="rotate(-90 80 80)"
            ><title>{`${label} ${((value / total) * 100).toFixed(1)}%`}</title></circle>;
            offset += len;
            return dash;
          })}
        </svg>
        <ul className="legend">
          {usable.map(([label, value], i) => (
            <li key={label}>
              <span className="swatch" style={{ background: PALETTE[i % PALETTE.length] }} />
              {label}<strong>{((value / total) * 100).toFixed(1)}%</strong>
            </li>
          ))}
        </ul>
      </div>
    </figure>
  );
}

/** Multi-series line over ordered periods (trend analysis). */
export function LineChart({ title, periods, series, unit = '' }: {
  title: string; periods: string[]; series: Array<{ name: string; values: Array<number | null> }>; unit?: string;
}) {
  const live = series.filter(s => s.values.some(v => typeof v === 'number'));
  if (!periods.length || !live.length) return <ChartEmpty title={title} />;

  const all = live.flatMap(s => s.values).filter((v): v is number => typeof v === 'number');
  const lo = Math.min(...all), hi = Math.max(...all);
  const pad = (hi - lo) * 0.1 || Math.abs(hi) * 0.1 || 1;
  const min = lo - pad, max = hi + pad;
  const W = 480, H = 200, L = 56, B = 28;

  const x = (i: number) => L + (i * (W - L - 8)) / Math.max(1, periods.length - 1);
  const y = (v: number) => H - B - ((v - min) / (max - min || 1)) * (H - B - 12);

  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="line-chart" role="img" aria-label={title}>
        {[0, 0.5, 1].map(t => {
          const v = min + t * (max - min);
          return <g key={t}>
            <line x1={L} x2={W - 8} y1={y(v)} y2={y(v)} className="grid" />
            <text x={L - 6} y={y(v) + 4} className="axis" textAnchor="end">{fmt(v, unit)}</text>
          </g>;
        })}
        {periods.map((p, i) => (
          <text key={p} x={x(i)} y={H - 8} className="axis" textAnchor="middle">{p}</text>
        ))}
        {live.map((s, si) => {
          const pts = s.values
            .map((v, i) => (typeof v === 'number' ? `${x(i)},${y(v)}` : null))
            .filter(Boolean).join(' ');
          return <g key={s.name}>
            <polyline points={pts} fill="none" stroke={PALETTE[si % PALETTE.length]} strokeWidth="2" />
            {s.values.map((v, i) => typeof v === 'number' ? (
              <circle key={i} cx={x(i)} cy={y(v)} r="3" fill={PALETTE[si % PALETTE.length]}>
                <title>{`${s.name} ${periods[i]}: ${fmt(v, unit)}`}</title>
              </circle>
            ) : null)}
          </g>;
        })}
      </svg>
      {live.length > 1 && (
        <ul className="legend">
          {live.map((s, i) => (
            <li key={s.name}><span className="swatch" style={{ background: PALETTE[i % PALETTE.length] }} />{s.name}</li>
          ))}
        </ul>
      )}
    </figure>
  );
}

/** Grouped bars comparing companies on one metric (peer comparison). */
export function GroupedBars({ title, categories, series, unit = '%' }: {
  title: string; categories: string[]; series: Array<{ name: string; values: Array<number | null> }>; unit?: string;
}) {
  const all = series.flatMap(s => s.values).filter((v): v is number => typeof v === 'number');
  if (!all.length) return <ChartEmpty title={title} />;
  const max = nice(Math.max(...all.map(Math.abs)));

  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <div className="grouped">
        {categories.map((cat, ci) => (
          <div className="group" key={cat}>
            <span className="bar-label">{cat}</span>
            <div className="group-bars">
              {series.map((s, si) => {
                const v = s.values[ci];
                return (
                  <div className="mini-row" key={s.name}>
                    <span className="mini-name">{s.name}</span>
                    <div className="bar-track">
                      <span className="bar-fill" style={{
                        left: 0,
                        width: typeof v === 'number' ? `${(Math.abs(v) / max) * 100}%` : '0%',
                        background: PALETTE[si % PALETTE.length],
                      }} />
                    </div>
                    <span className="bar-value">{typeof v === 'number' ? fmt(v, unit) : '—'}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </figure>
  );
}

/** An absent chart says why. A blank space reads as a broken page. */
export function ChartEmpty({ title }: { title: string }) {
  return (
    <figure className="chart empty-chart">
      <figcaption>{title}</figcaption>
      <p>此期間沒有可繪製的數值（欄位缺漏或不適用）。</p>
    </figure>
  );
}
