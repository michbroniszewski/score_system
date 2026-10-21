<script setup lang="ts">
import { computed } from 'vue'
import { formatStart, score, STATUS_LABELS } from '../api/format'
import { useApi } from '../api/useApi'
import type { MatchOut } from '../api/types'
import LoadState from '../components/LoadState.vue'
import { useCompetition } from './competition'

const props = defineProps<{ slug: string }>()
const competition = useCompetition()
const { data, error, loading } = useApi<MatchOut[]>(() => `competitions/${props.slug}/matches`)

// The API lists matches by round already; group them for one heading per round.
const rounds = computed(() => {
  const byRound = new Map<number, MatchOut[]>()
  for (const match of data.value ?? []) {
    byRound.set(match.round, [...(byRound.get(match.round) ?? []), match])
  }
  return [...byRound.entries()].map(([round, matches]) => ({ round, matches }))
})
</script>

<template>
  <LoadState
    :loading="loading"
    :error="error"
  >
    <section
      v-for="{ round, matches } in rounds"
      :key="round"
    >
      <h2>Kolejka {{ round }}</h2>
      <ul class="matches">
        <li
          v-for="match in matches"
          :key="match.id"
        >
          <RouterLink :to="{ name: 'match', params: { slug, matchId: match.id } }">
            <span class="teams">{{ match.home.name }} – {{ match.away.name }}</span>
            <span class="score">{{ score(match) }}</span>
          </RouterLink>
          <span class="meta">
            {{ formatStart(match.starts_at, competition?.timezone ?? 'UTC') }}
            <template v-if="match.venue">· {{ match.venue }}</template>
            <template v-if="match.status !== 'scheduled' && match.status !== 'played'">
              · {{ STATUS_LABELS[match.status] }}
            </template>
          </span>
        </li>
      </ul>
    </section>
  </LoadState>
</template>
