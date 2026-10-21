<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { send } from '../api/client'
import { formatStart, score, statLabel, STATUS_LABELS } from '../api/format'
import type {
  CompetitionOut,
  EventOut,
  MatchOut,
  PresetOut,
  RosterEntryOut,
} from '../api/types'
import { useApi } from '../api/useApi'
import { utcToZoned, zonedToUtc } from '../api/zoned'
import LoadState from '../components/LoadState.vue'
import { useAction } from './useAction'

const props = defineProps<{ slug: string; matchId: string }>()
const competition = useApi<CompetitionOut>(() => `competitions/${props.slug}`)
const match = useApi<MatchOut>(() => `matches/${props.matchId}`)
const events = useApi<EventOut[]>(() => `matches/${props.matchId}/events`)
// Empty paths wait until the competition and the match are loaded.
const preset = useApi<PresetOut>(() =>
  competition.data.value ? `presets/${competition.data.value.preset}` : '',
)
const homeRoster = useApi<RosterEntryOut[]>(() =>
  match.data.value ? `competitions/${props.slug}/teams/${match.data.value.home.id}/roster` : '',
)
const awayRoster = useApi<RosterEntryOut[]>(() =>
  match.data.value ? `competitions/${props.slug}/teams/${match.data.value.away.id}/roster` : '',
)

const timeZone = computed(() => competition.data.value?.timezone ?? 'UTC')
const status = computed(() => match.data.value?.status)
const isOpen = computed(() => status.value === 'scheduled' || status.value === 'postponed')
const canRecord = computed(() => status.value !== undefined && status.value !== 'cancelled')
const setsToWin = computed(() => preset.data.value?.sets_to_win ?? 3)

// The forms start from the stored match and are reset whenever it is reloaded.
const schedule = reactive({ startsAt: '', venue: '' })
const sets = ref<{ home: number | ''; away: number | '' }[]>([])
watch(
  [() => match.data.value, () => competition.data.value, setsToWin],
  ([m]) => {
    if (!m) return
    schedule.startsAt = m.starts_at ? utcToZoned(m.starts_at, timeZone.value) : ''
    schedule.venue = m.venue ?? ''
    sets.value = m.sets.length
      ? m.sets.map((s) => ({ ...s }))
      : Array.from({ length: setsToWin.value }, () => ({ home: '', away: '' }))
  },
  { immediate: true },
)

const changing = useAction()
async function change(path: string, body?: unknown) {
  if (await changing.run(() => send('POST', `matches/${props.matchId}/${path}`, body))) {
    match.reload()
  }
}

function reschedule() {
  const startsAt = zonedToUtc(schedule.startsAt, timeZone.value)
  return change('reschedule', { starts_at: startsAt, venue: schedule.venue || null })
}

function recordResult() {
  const filled = sets.value.filter((s) => s.home !== '' && s.away !== '')
  return change('result', { sets: filled })
}

const walkoverWinner = ref('')

const roster = computed(() => {
  const m = match.data.value
  if (!m) return {}
  return {
    [m.home.id]: homeRoster.data.value ?? [],
    [m.away.id]: awayRoster.data.value ?? [],
  } as Record<string, RosterEntryOut[]>
})
const teamName = (id: string) =>
  [match.data.value?.home, match.data.value?.away].find((t) => t?.id === id)?.name ?? ''

const event = reactive({ teamId: '', playerId: '', stat: '', value: 1 })
const players = computed(() => roster.value[event.teamId] ?? [])
const eventing = useAction()
async function addEvent() {
  const body = {
    team_id: event.teamId,
    player_id: event.playerId,
    stat: event.stat,
    value: event.value,
  }
  if (await eventing.run(() => send('POST', `matches/${props.matchId}/events`, body))) {
    event.playerId = ''
    event.value = 1
    events.reload()
  }
}
async function deleteEvent(id: string) {
  if (await eventing.run(() => send('DELETE', `events/${id}`))) events.reload()
}
</script>

<template>
  <LoadState
    :loading="match.loading.value || competition.loading.value"
    :error="match.error.value ?? competition.error.value"
  >
    <template v-if="match.data.value">
      <p class="meta">
        <RouterLink :to="{ name: 'admin-competition', params: { slug } }">
          ← {{ competition.data.value?.name }}
        </RouterLink>
      </p>
      <h1>{{ match.data.value.home.name }} – {{ match.data.value.away.name }}</h1>
      <p class="meta">
        Kolejka {{ match.data.value.round }} ·
        {{ formatStart(match.data.value.starts_at, timeZone) }} ·
        {{ STATUS_LABELS[match.data.value.status] }}
        <strong v-if="score(match.data.value)"> {{ score(match.data.value) }}</strong>
      </p>
      <p
        v-if="changing.error.value"
        class="error"
      >
        {{ changing.error.value }}
      </p>

      <template v-if="isOpen">
        <h2>Termin</h2>
        <form
          class="form"
          @submit.prevent="reschedule"
        >
          <label>Początek ({{ timeZone }}) <input
            v-model="schedule.startsAt"
            type="datetime-local"
            required
          ></label>
          <label>Miejsce <input v-model="schedule.venue"></label>
          <button :disabled="changing.busy.value">
            Zapisz termin
          </button>
        </form>
        <p class="actions">
          <button
            v-if="status === 'scheduled'"
            :disabled="changing.busy.value"
            @click="change('postpone')"
          >
            Przełóż
          </button>
          <button
            :disabled="changing.busy.value"
            @click="change('cancel')"
          >
            Odwołaj mecz
          </button>
        </p>
      </template>

      <template v-if="canRecord">
        <h2>Wynik</h2>
        <form
          class="form"
          @submit.prevent="recordResult"
        >
          <div
            v-for="(set, i) in sets"
            :key="i"
            class="set-row"
          >
            <span>Set {{ i + 1 }}</span>
            <input
              v-model.number="set.home"
              type="number"
              min="0"
              :aria-label="`Set ${i + 1}: ${match.data.value.home.name}`"
            >
            <span>:</span>
            <input
              v-model.number="set.away"
              type="number"
              min="0"
              :aria-label="`Set ${i + 1}: ${match.data.value.away.name}`"
            >
          </div>
          <p class="actions">
            <button
              type="button"
              :disabled="sets.length >= 2 * setsToWin - 1"
              @click="sets.push({ home: '', away: '' })"
            >
              Dodaj set
            </button>
            <button
              type="button"
              :disabled="sets.length <= 1"
              @click="sets.pop()"
            >
              Usuń set
            </button>
            <button :disabled="changing.busy.value">
              Zapisz wynik
            </button>
          </p>
        </form>

        <h2>Walkower</h2>
        <form
          class="form"
          @submit.prevent="change('walkover', { winner: walkoverWinner })"
        >
          <label>Zwycięzca
            <select
              v-model="walkoverWinner"
              required
            >
              <option
                v-for="team in [match.data.value.home, match.data.value.away]"
                :key="team.id"
                :value="team.id"
              >{{ team.name }}</option>
            </select>
          </label>
          <button :disabled="changing.busy.value">
            Zapisz walkower
          </button>
        </form>
      </template>

      <template v-if="status === 'played'">
        <h2>Statystyki</h2>
        <div class="table-wrap">
          <table>
            <tbody>
              <tr
                v-for="e in events.data.value"
                :key="e.id"
              >
                <td class="left">
                  {{ e.player.name }}
                </td>
                <td class="left">
                  {{ teamName(e.team_id) }}
                </td>
                <td class="left">
                  {{ statLabel(e.stat) }}
                </td>
                <td>{{ e.value }}</td>
                <td>
                  <button
                    :disabled="eventing.busy.value"
                    @click="deleteEvent(e.id)"
                  >
                    Usuń
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <form
          class="form"
          @submit.prevent="addEvent"
        >
          <label>Drużyna
            <select
              v-model="event.teamId"
              required
              @change="event.playerId = ''"
            >
              <option
                v-for="team in [match.data.value.home, match.data.value.away]"
                :key="team.id"
                :value="team.id"
              >{{ team.name }}</option>
            </select>
          </label>
          <label>Zawodnik
            <select
              v-model="event.playerId"
              required
            >
              <option
                v-for="entry in players"
                :key="entry.id"
                :value="entry.player.id"
              >{{ entry.number ?? '' }} {{ entry.player.first_name }} {{ entry.player.last_name }}</option>
            </select>
          </label>
          <label>Statystyka
            <select
              v-model="event.stat"
              required
            >
              <option
                v-for="stat in preset.data.value?.stats"
                :key="stat"
                :value="stat"
              >{{ statLabel(stat) }}</option>
            </select>
          </label>
          <label>Wartość <input
            v-model.number="event.value"
            type="number"
            min="1"
            required
          ></label>
          <button :disabled="eventing.busy.value">
            Dodaj statystykę
          </button>
          <p
            v-if="eventing.error.value"
            class="error"
          >
            {{ eventing.error.value }}
          </p>
        </form>
      </template>
    </template>
  </LoadState>
</template>
