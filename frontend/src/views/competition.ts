import { inject, type InjectionKey, type Ref } from 'vue'
import type { CompetitionOut } from '../api/types'

// The competition loaded by CompetitionLayout, for its tabs (e.g. its time zone).
export const COMPETITION: InjectionKey<Ref<CompetitionOut | null>> = Symbol('competition')

export function useCompetition(): Ref<CompetitionOut | null> {
  const competition = inject(COMPETITION)
  if (competition === undefined) throw new Error('used outside CompetitionLayout')
  return competition
}
