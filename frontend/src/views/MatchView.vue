<script setup lang="ts">
import { computed } from 'vue'
import { formatStart, matchLabel, score, statLabel, STATUS_LABELS } from '../api/format'
import { useApi } from '../api/useApi'
import type { EventOut, MatchOut } from '../api/types'
import LoadState from '../components/LoadState.vue'
import { useCompetition } from './competition'

const props = defineProps<{ slug: string; matchId: string }>()
const competition = useCompetition()
const match = useApi<MatchOut>(() => `matches/${props.matchId}`)
const events = useApi<EventOut[]>(() => `matches/${props.matchId}/events`)

const winner = computed(() => {
  const m = match.data.value
  if (m?.walkover_winner == null) return null
  return m.home.id === m.walkover_winner ? m.home.name : m.away.name
})
</script>

<template>
  <LoadState
    :loading="match.loading.value"
    :error="match.error.value"
  >
    <template v-if="match.data.value">
      <h2>
        {{ match.data.value.home.name }} {{ score(match.data.value) || '–' }}
        {{ match.data.value.away.name }}
      </h2>
      <p class="meta">
        {{ matchLabel(match.data.value) }} ·
        {{ formatStart(match.data.value.starts_at, competition?.timezone ?? 'UTC') }}
        <template v-if="match.data.value.venue">
          · {{ match.data.value.venue }}
        </template>
        · {{ STATUS_LABELS[match.data.value.status] }}
      </p>
      <p v-if="winner">
        Walkower dla: {{ winner }}
      </p>
      <ul
        v-if="match.data.value.sets.length"
        class="sets"
      >
        <li
          v-for="(set, i) in match.data.value.sets"
          :key="i"
        >
          Set {{ i + 1 }}: {{ set.home }}:{{ set.away }}
        </li>
      </ul>
      <LoadState
        :loading="events.loading.value"
        :error="events.error.value"
      >
        <template v-if="events.data.value?.length">
          <h3>Statystyki meczu</h3>
          <ul>
            <li
              v-for="event in events.data.value"
              :key="event.id"
            >
              {{ event.player.name }}: {{ statLabel(event.stat) }} {{ event.value }}
            </li>
          </ul>
        </template>
      </LoadState>
    </template>
  </LoadState>
</template>
