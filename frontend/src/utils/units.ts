const KG_TO_LBS = 2.20462;

export function convertWeight(weight: number, toUnit: 'kg' | 'lbs'): number {
  if (weight <= 0) return 0;
  if (toUnit === 'lbs') {
    return Math.round(weight * KG_TO_LBS * 10) / 10;
  } else {
    return Math.round((weight / KG_TO_LBS) * 10) / 10;
  }
}

export function calculate1RM(weight: number, reps: number): number {
  if (reps <= 0 || weight <= 0) return 0;
  if (reps === 1) return weight;
  // McGlothin formula is only valid for reps < 37. 
  // For higher reps, we cap it to avoid division by zero and unrealistic values.
  const effectiveReps = Math.min(reps, 36);
  return weight * (36 / (37 - effectiveReps));
}
