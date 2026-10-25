<script setup lang="ts">
import { formatStart, score, sidesLabel, winsLabel } from '../api/format'
import { useApi } from '../api/useApi'
import type { PlayoffOut } from '../api/types'
import LoadState from '../components/LoadState.vue'
import { useCompetition } from './competition'

const props = defineProps<{ slug: string }>()
const competition = useCompetition()
const playoff = useApi<PlayoffOut>(() => `competitions/${props.slug}/playoff`)
</script>

<template>
  <LoadState
    :loading="playoff.loading.value"
    :error="playoff.error.value"
  >
    <template v-if="playoff.data.value">
      <p class="meta">
        {{ playoff.data.value.format }}
      </p>
      <template v-if="playoff.data.value.started">
        <h2>Klasyfikacja końcowa</h2>
        <ol class="places">
          <li
            v-for="place in playoff.data.value.places"
            :key="place.place"
          >
            {{ place.team?.name ?? 'do ustalenia' }}
          </li>
        </ol>
      </template>
      <p
        v-else
        class="notice"
      >
        Play-off rozpocznie się po zakończeniu fazy zasadniczej.
      </p>

      <h2>Serie</h2>
      <section
        v-for="series in playoff.data.value.series"
        :key="series.key"
        class="series"
      >
        <h3>
          Seria {{ series.key }}
          <span class="meta">· {{ winsLabel(series.wins) }}</span>
        </h3>
        <p v-if="series.home && series.away">
          <span :class="{ strong: series.winner?.id === series.home.id }">{{ series.home.name }}</span>
          {{ series.home_wins }}:{{ series.away_wins }}
          <span :class="{ strong: series.winner?.id === series.away.id }">{{ series.away.name }}</span>
        </p>
        <p
          v-else
          class="meta"
        >
          {{ sidesLabel(series.sides) }}
        </p>
        <ul class="matches">
          <li
            v-for="match in series.matches"
            :key="match.id"
          >
            <RouterLink :to="{ name: 'match', params: { slug, matchId: match.id } }">
              <span class="teams">Mecz {{ match.round }}: {{ match.home.name }} – {{ match.away.name }}</span>
              <span class="score">{{ score(match) }}</span>
            </RouterLink>
            <span class="meta">
              {{ formatStart(match.starts_at, competition?.timezone ?? 'UTC') }}
              <template v-if="match.venue">· {{ match.venue }}</template>
            </span>
          </li>
        </ul>
      </section>
    </template>
  </LoadState>
</template>
