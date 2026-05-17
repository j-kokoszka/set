const KG_TO_LBS = 2.20462;

export function convertWeight(weight: number, toUnit: 'kg' | 'lbs'): number {
  if (weight <= 0) return 0;
  if (toUnit === 'lbs') {
    return Math.round(weight * KG_TO_LBS * 10) / 10;
  } else {
    return Math.round((weight / KG_TO_LBS) * 10) / 10;
  }
}
