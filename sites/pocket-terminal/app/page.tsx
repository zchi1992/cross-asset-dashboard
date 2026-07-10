import type { Metadata } from "next";
import { snapshot, type ScatterAsset, type SnapshotAsset } from "./snapshot-data";

export const metadata: Metadata = {
  title: "Cross Asset Pocket Terminal",
  description: "Private cross-asset snapshot for mobile review.",
};

export default function Home() {
  const leadShare = Math.round((snapshot.stateCounts.rs.Lead / snapshot.assetCount) * 100);
  const leveragingShare = Math.round((snapshot.stateCounts.funding.Leveraging / snapshot.assetCount) * 100);

  return (
    <main className="terminal">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Cross Asset Pocket Terminal</p>
          <h1>{snapshot.date}</h1>
          <p className="hero-text">
            {snapshot.assetCount.toLocaleString()} rows across {snapshot.uniqueAssets.toLocaleString()} assets, distilled
            for a private phone-sized read.
          </p>
        </div>
        <div className="hero-panel" aria-label="Snapshot coverage">
          <Metric label="Lead share" value={`${leadShare}%`} />
          <Metric label="Leveraging" value={`${leveragingShare}%`} />
          <Metric label="Long setups" value={snapshot.longCandidateCount.toString()} />
          <Metric label="Short setups" value={snapshot.shortCandidateCount.toString()} />
        </div>
      </header>

      <section className="summary-grid" aria-label="Asset class summary">
        {snapshot.classSummary.map((item) => (
          <article className="class-tile" key={item.assetClass}>
            <div>
              <p className="tile-kicker">{item.assetClass}</p>
              <h2>{item.count.toLocaleString()}</h2>
            </div>
            <dl>
              <Row label="Avg trend" value={formatScore(item.avgTrend)} />
              <Row label="Avg RS" value={formatScore(item.avgRs)} />
              <Row label="Avg velocity" value={formatScore(item.avgVelocity)} />
              <Row label="Leader" value={`${item.leader} ${formatScore(item.leaderScore)}`} />
              <Row label="Weakest" value={`${item.weakest} ${formatScore(item.weakScore)}`} />
            </dl>
          </article>
        ))}
      </section>

      <section className="map-section" aria-label="Relative strength and velocity map">
        <div className="section-heading">
          <p className="eyebrow">RS x Velocity</p>
          <h2>Score Map</h2>
        </div>
        <div className="score-map">
          <span className="axis-label axis-left">Velocity</span>
          <span className="axis-label axis-bottom">Relative Strength</span>
          <div className="zero zero-x" />
          <div className="zero zero-y" />
          {snapshot.scatter.map((item) => (
            <MapPoint item={item} key={item.symbol} />
          ))}
        </div>
      </section>

      <section className="lists" aria-label="Candidate lists">
        <CandidateList title="Long Pressure" items={snapshot.longs} scoreKey="longScore" />
        <CandidateList title="Weak Pressure" items={snapshot.shorts} scoreKey="shortScore" />
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function CandidateList({
  title,
  items,
  scoreKey,
}: {
  title: string;
  items: readonly SnapshotAsset[];
  scoreKey: "longScore" | "shortScore";
}) {
  return (
    <article className="candidate-panel">
      <div className="section-heading">
        <p className="eyebrow">{title}</p>
        <h2>{items[0]?.symbol ?? "None"}</h2>
      </div>
      <ol>
        {items.map((item) => (
          <li key={item.symbol}>
            <div className="asset-title">
              <strong>{item.symbol}</strong>
              <span>{item.name}</span>
            </div>
            <div className="score-strip">
              <Score label="T" value={item.trend} />
              <Score label="RS" value={item.rs} />
              <Score label="V" value={item.velocity} />
              <Score label="S" value={item[scoreKey] ?? 0} />
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <span className={value < 0 ? "score negative" : "score"}>
      {label} {formatScore(value)}
    </span>
  );
}

function MapPoint({ item }: { item: ScatterAsset }) {
  const x = clamp(((item.rs + 20) / 180) * 100, 2, 98);
  const y = clamp(100 - ((item.velocity + 110) / 220) * 100, 2, 98);
  const positive = item.velocity >= 0;

  return (
    <span
      className={positive ? "map-point positive" : "map-point negative"}
      style={{ left: `${x}%`, top: `${y}%` }}
      title={`${item.symbol}: RS ${formatScore(item.rs)}, velocity ${formatScore(item.velocity)}`}
    >
      {item.symbol}
    </span>
  );
}

function formatScore(value: number) {
  return value.toFixed(Math.abs(value) >= 100 ? 0 : 1);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
