export type SnapshotAsset = {
  symbol: string;
  name: string;
  assetClass: string;
  trend: number;
  rs: number;
  velocity: number;
  funding: number;
  fundingState: "Leveraging" | "Deleveraging";
  rsState: "Lag" | "Weakening" | "Improving" | "Lead";
  monthly?: string;
  weekly?: string;
  daily?: string;
  longScore?: number;
  shortScore?: number;
};

export type ScatterAsset = Pick<
  SnapshotAsset,
  "symbol" | "name" | "assetClass" | "rs" | "velocity" | "trend" | "fundingState" | "rsState"
>;

export const snapshot = {
  date: "2026-07-09",
  dateCount: 43,
  assetCount: 1190,
  uniqueAssets: 1128,
  classCount: 2,
  longCandidateCount: 20,
  shortCandidateCount: 0,
  stateCounts: {
    rs: { Lead: 540, Improving: 441, Lag: 67, Weakening: 142 },
    funding: { Leveraging: 483, Deleveraging: 707 },
    quadrants: { lead_leveraging: 560, lead_deleveraging: 630 },
  },
  classSummary: [
    {
      assetClass: "instruments",
      count: 956,
      avgTrend: 20.9,
      avgRs: 107.6,
      avgVelocity: -6.5,
      leader: "BBH",
      leaderScore: 305,
      weakest: "ZROZ",
      weakScore: 52,
    },
    {
      assetClass: "core",
      count: 234,
      avgTrend: 18.1,
      avgRs: 106.9,
      avgVelocity: 0,
      leader: "USMV",
      leaderScore: 281.6,
      weakest: "EURGBP",
      weakScore: 33,
    },
  ],
  longs: [
    asset("BBH", "VanEck Biotech ETF", "instruments", 88, 120.3, 96.7, 100, "Leveraging", "Lead", "up", "up", "up", 305),
    asset("DSTL", "Distillate US Fundamental Stability & Value ETF", "instruments", 84, 123.4, 91.3, 71.9, "Leveraging", "Lead", "up", "up", "up", 298.7),
    asset("IBB", "iShares Biotechnology ETF", "instruments", 88.8, 117.2, 90.6, 100, "Leveraging", "Lead", "up", "up", "up", 296.6),
    asset("EWS", "iShares MSCI Singapore ETF", "instruments", 82.2, 137.6, 75.3, 80.9, "Leveraging", "Lead", "up", "up", "up", 295),
    asset("SPLV", "Invesco S&P 500 Low Volatility ETF", "instruments", 83.5, 124.2, 81.1, 75.3, "Leveraging", "Lead", "up", "up", "up", 288.8),
    asset("DGRO", "iShares Core Dividend Growth ETF", "instruments", 93.3, 122.2, 73.2, 94.8, "Leveraging", "Lead", "up", "up", "up", 288.7),
    asset("SPGP", "Invesco S&P 500 GARP ETF", "instruments", 95.9, 120.5, 71.4, 86, "Leveraging", "Lead", "up", "up", "up", 287.8),
    asset("PKW", "Invesco Buyback Achievers ETF", "instruments", 97.3, 119.6, 70.7, 84.7, "Leveraging", "Lead", "up", "up", "up", 287.5),
  ],
  shorts: [
    asset("ZROZ", "PIMCO 25+ Year Zero Coupon US Treasury Index Exchange-Traded Fund", "instruments", -51, 93.6, -94.6, 43.9, "Deleveraging", "Lag", "down", "neutral", "down", undefined, 52),
    asset("EDV", "Vanguard Extended Duration Treasury ETF", "instruments", -51, 94.7, -94, 43.3, "Deleveraging", "Lag", "down", "neutral", "down", undefined, 50.3),
    asset("TMF", "Direxion Daily 20+ Year Treasury Bull 3X ETF", "instruments", -50.4, 90.3, -79.3, 39.4, "Deleveraging", "Lag", "down", "neutral", "down", undefined, 39.4),
    asset("EURGBP", "EUR/GBP", "core", -38.3, 103.5, -98.2, 12.6, "Deleveraging", "Improving", "neutral", "down", "down", undefined, 33),
    asset("SA1!", "Soda Ash Futures", "core", -70.2, 96.5, -54.9, 7.2, "Deleveraging", "Improving", "down", "down", "down", undefined, 28.6),
    asset("LABD", "Direxion Daily S&P Biotech Bear 3X ETF", "instruments", -90.8, 94, -31.7, 0, "Deleveraging", "Improving", "down", "down", "down", undefined, 28.6),
    asset("TLT", "iShares 20+ Year Treasury Bond ETF", "core", -50.4, 110.6, -87.6, 43.4, "Deleveraging", "Lead", "down", "neutral", "down", undefined, 27.4),
    asset("CHAU", "Direxion Daily CSI 300 China A Share Bull 2X ETF", "instruments", -10.2, 75.2, -88.8, 56.7, "Deleveraging", "Lag", "neutral", "neutral", "down", undefined, 23.8),
  ],
  scatter: [
    point("BBH", "VanEck Biotech ETF", "instruments", 120.3, 96.7, 88, "Leveraging", "Lead"),
    point("DSTL", "Distillate US Fundamental Stability & Value ETF", "instruments", 123.4, 91.3, 84, "Leveraging", "Lead"),
    point("IBB", "iShares Biotechnology ETF", "instruments", 117.2, 90.6, 88.8, "Leveraging", "Lead"),
    point("EWS", "iShares MSCI Singapore ETF", "instruments", 137.6, 75.3, 82.2, "Leveraging", "Lead"),
    point("SPLV", "Invesco S&P 500 Low Volatility ETF", "instruments", 124.2, 81.1, 83.5, "Leveraging", "Lead"),
    point("DGRO", "iShares Core Dividend Growth ETF", "instruments", 122.2, 73.2, 93.3, "Leveraging", "Lead"),
    point("SPGP", "Invesco S&P 500 GARP ETF", "instruments", 120.5, 71.4, 95.9, "Leveraging", "Lead"),
    point("PKW", "Invesco Buyback Achievers ETF", "instruments", 119.6, 70.7, 97.3, "Leveraging", "Lead"),
    point("USMV", "iShares MSCI USA Min Vol Factor ETF", "core", 123.9, 95.6, 62.1, "Leveraging", "Lead"),
    point("CALF", "Pacer US Small Cap Cash Cows ETF", "instruments", 115.6, 77.8, 84.6, "Leveraging", "Lead"),
    point("ZROZ", "PIMCO 25+ Year Zero Coupon US Treasury Index Exchange-Traded Fund", "instruments", 93.6, -94.6, -51, "Deleveraging", "Lag"),
    point("EDV", "Vanguard Extended Duration Treasury ETF", "instruments", 94.7, -94, -51, "Deleveraging", "Lag"),
    point("TMF", "Direxion Daily 20+ Year Treasury Bull 3X ETF", "instruments", 90.3, -79.3, -50.4, "Deleveraging", "Lag"),
    point("EURGBP", "EUR/GBP", "core", 103.5, -98.2, -38.3, "Deleveraging", "Improving"),
    point("SA1!", "Soda Ash Futures", "core", 96.5, -54.9, -70.2, "Deleveraging", "Improving"),
    point("LABD", "Direxion Daily S&P Biotech Bear 3X ETF", "instruments", 94, -31.7, -90.8, "Deleveraging", "Improving"),
    point("TLT", "iShares 20+ Year Treasury Bond ETF", "core", 110.6, -87.6, -50.4, "Deleveraging", "Lead"),
    point("CHAU", "Direxion Daily CSI 300 China A Share Bull 2X ETF", "instruments", 75.2, -88.8, -10.2, "Deleveraging", "Lag"),
    point("OZEM", "Roundhill GLP-1 & Weight Loss ETF", "instruments", 129.6, 96.2, -13, "Leveraging", "Lead"),
    point("THNR", "Amplify Weight Loss Drug & Treatment ETF", "instruments", 128.2, 97.2, 13.6, "Leveraging", "Lead"),
    point("SGOV", "iShares 0-3 Month Treasury Bond ETF", "instruments", 121.1, -99.4, -12.5, "Deleveraging", "Lead"),
    point("EDEN", "iShares MSCI Denmark ETF", "instruments", 125.2, 95.2, 12.5, "Leveraging", "Lead"),
    point("TBIL", "F/m US Treasury 3 Month Bill Fund", "instruments", 121.4, -98.8, -13.3, "Deleveraging", "Lead"),
    point("BIL", "State Street SPDR Bloomberg 1-3 Month T-Bill ETF", "instruments", 121.1, -97.5, 0, "Deleveraging", "Lead"),
    point("159985", "Hua Xia Feed Soymeal Futures ETF", "instruments", 118.3, 99.5, 58.3, "Leveraging", "Lead"),
    point("ESPO", "VanEck Video Gaming and eSports ETF", "instruments", 116.6, 99.2, -14.2, "Leveraging", "Lead"),
    point("MINT", "PIMCO Enhanced Short Maturity Active ETF", "instruments", 121.3, -94.4, 63.7, "Deleveraging", "Lead"),
    point("USFR", "WisdomTree Floating Rate Treasury Fund", "instruments", 121.4, -93.8, 0, "Deleveraging", "Lead"),
  ],
} as const;

function asset(
  symbol: string,
  name: string,
  assetClass: string,
  trend: number,
  rs: number,
  velocity: number,
  funding: number,
  fundingState: SnapshotAsset["fundingState"],
  rsState: SnapshotAsset["rsState"],
  monthly?: string,
  weekly?: string,
  daily?: string,
  longScore?: number,
  shortScore?: number,
): SnapshotAsset {
  return {
    symbol,
    name,
    assetClass,
    trend,
    rs,
    velocity,
    funding,
    fundingState,
    rsState,
    monthly,
    weekly,
    daily,
    longScore,
    shortScore,
  };
}

function point(
  symbol: string,
  name: string,
  assetClass: string,
  rs: number,
  velocity: number,
  trend: number,
  fundingState: SnapshotAsset["fundingState"],
  rsState: SnapshotAsset["rsState"],
): ScatterAsset {
  return { symbol, name, assetClass, rs, velocity, trend, fundingState, rsState };
}
