# Opportunities Screening Rules

This note records the two current long-side opportunity screens discussed for the local processed `core + instruments` universe.

## Shared Field Mapping

- `trend_score`: `capped_final_trend_score`
- `funding_state`: mapped from `funding_signal_direction`
  - `long_candidate` -> `Leveraging`
  - `short_candidate` -> `Deleveraging`
- `leverage_score`: `funding_signal_strength`
- `leverage_duration`: `funding_current_leverage_state_duration`
- `leverage_velocity`: weighted leverage velocity metric

## Strong Long Screen

Use this screen for confirmed relative-strength leaders with fresh or active leverage support.

### Filter

```text
current_relative_state in {"Lead", "Improving"}
early_reversal > 100
funding_state == "Leveraging"
trend_score > 20
weekly_trend == "up"
```

### Sort

```text
funding_current_leverage_state_duration ascending
funding_signal_strength descending
trend_score descending
dataset_type ascending
asset_code ascending
asset_name ascending
```

### Intent

- Prefer assets that are already leading or improving in relative strength.
- Require leverage to be actively adding.
- Prefer newly started leverage regimes first, then stronger leverage score and stronger trend score.

## Candidate Long Screen

Use this screen for improving relative-strength names where the trend is not broken and funding is either adding leverage or no longer meaningfully deleveraging.

### Filter

```text
current_relative_state == "Improving"
early_reversal > 100
trend_score > 20
daily_trend != "down"
weekly_trend != "down"
(
  funding_state == "Leveraging"
  OR (
    funding_state == "Deleveraging"
    AND leverage_velocity > -5
  )
)
```

No active filter on:

```text
strength_momentum
relative_strength
rs_score
leverage_score
```

### Sort

Primary sort by funding state:

```text
funding_state_sort ascending
```

where:

```text
Leveraging -> 0
Deleveraging -> 1
other -> 2
```

Within `Leveraging`:

```text
funding_current_leverage_state_duration ascending
```

Within `Deleveraging`:

```text
leverage_velocity descending
```

Tie-breakers:

```text
early_reversal descending
strength_momentum ascending
relative_strength ascending
funding_signal_strength ascending
leverage_velocity descending
dataset_type ascending
asset_code ascending
asset_name ascending
```

### Intent

- Rank fresh `Leveraging` candidates before `Deleveraging` candidates.
- Within `Leveraging`, prefer shorter leverage-state duration as a fresher entry signal.
- Within `Deleveraging`, only keep mild deleveraging or leverage recovery (`leverage_velocity > -5`), then prefer the highest leverage velocity.
- Use ER, SM, RS, leverage score, and stable asset identity only as tie-breakers after the funding-state priority.
