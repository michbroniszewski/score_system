<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { send } from '../api/client'
import { score, STATUS_LABELS } from '../api/format'
import type { CompetitionOut, MatchOut, PlayoffOut, TeamOut } from '../api/types'
import { useApi } from '../api/useApi'
import LoadState from '../components/LoadState.vue'
import { useAction } from './useAction'

const props = defineProps<{ slug: string }>()
const competition = useApi<CompetitionOut>(() => `competitions/${props.slug}`)
const teams = useApi<TeamOut[]>(() => `competitions/${props.slug}/teams`)
const matches = useApi<MatchOut[]>(() => `competitions/${props.slug}/matches`)
const savedTeams = useApi<TeamOut[]>(() => 'teams')

// All four must load: without the matches the page would offer forms that only work
// before the fixtures exist.
const sources = [competition, teams, matches, savedTeams]
const loading = computed(() => sources.some((s) => s.loading.value))
const loadError = computed(() => sources.find((s) => s.error.value)?.error.value ?? null)

// Teams can be entered only until the fixtures are generated.
const hasFixtures = computed(() => (matches.data.value?.length ?? 0) > 0)
// The play-off starts from the final table: every regular-season match must be over.
const seasonOver = computed(
  () =>
    hasFixtures.value &&
    !matches.data.value?.some((m) => m.status === 'scheduled' || m.status === 'postponed'),
)
const offered = computed(() =>
  (savedTeams.data.value ?? []).filter((t) => !teams.data.value?.some((e) => e.id === t.id)),
)
const rounds = computed(() => {
  const byRound = new Map<number, MatchOut[]>()
  for (const match of matches.data.value ?? []) {
    byRound.set(match.round, [...(byRound.get(match.round) ?? []), match])
  }
  return [...byRound.entries()]
})

// Only a competition with a play-off format has one; the path waits for the competition.
const playoff = useApi<PlayoffOut>(() =>
  competition.data.value?.playoff ? `competitions/${props.slug}/playoff` : '',
)
const starting = useAction()
async function startPlayoff() {
  if (!window.confirm('Rozpocząć play-off? Pary powstaną z obecnej tabeli i nie da się tego cofnąć.')) {
    return
  }
  if (await starting.run(() => send('POST', `competitions/${props.slug}/playoff`))) {
    playoff.reload()
  }
}

const entry = reactive({ name: '', saved: false, savedId: '' })
const entering = useAction()
async function enterTeam() {
  const body = entry.savedId
    ? { team_id: entry.savedId }
    : { team: { name: entry.name, saved: entry.saved } }
  if (await entering.run(() => send('POST', `competitions/${props.slug}/teams`, body))) {
    Object.assign(entry, { name: '', saved: false, savedId: '' })
    teams.reload()
    savedTeams.reload()
  }
}

const double = ref(false)
const generating = useAction()
async function generate() {
  const body = { double: double.value }
  if (await generating.run(() => send('POST', `competitions/${props.slug}/fixtures`, body))) {
    matches.reload()
  }
}
</script>

<template>
  <LoadState
    :loading="loading"
    :error="loadError"
  >
    <h1>{{ competition.data.value?.name }}</h1>
    <p class="meta">
      <RouterLink :to="{ name: 'standings', params: { slug } }">
        Zobacz stronę publiczną
      </RouterLink>
    </p>

    <h2>Drużyny</h2>
    <ul class="cards">
      <li
        v-for="team in teams.data.value"
        :key="team.id"
      >
        <RouterLink :to="{ name: 'admin-roster', params: { slug, teamId: team.id } }">
          {{ team.name }}
        </RouterLink>
        <span class="meta"> · skład</span>
      </li>
    </ul>
    <form
      v-if="!hasFixtures"
      class="form"
      @submit.prevent="enterTeam"
    >
      <label v-if="offered.length">Drużyna z bazy
        <select v-model="entry.savedId">
          <option value="">nowa drużyna</option>
          <option
            v-for="team in offered"
            :key="team.id"
            :value="team.id"
          >{{ team.name }}</option>
        </select>
      </label>
      <template v-if="!entry.savedId">
        <label>Nazwa nowej drużyny <input
          v-model="entry.name"
          required
        ></label>
        <label class="check"><input
          v-model="entry.saved"
          type="checkbox"
        > zapamiętaj w bazie drużyn</label>
      </template>
      <button :disabled="entering.busy.value">
        Dodaj drużynę
      </button>
      <p
        v-if="entering.error.value"
        class="error"
      >
        {{ entering.error.value }}
      </p>
    </form>

    <template v-if="competition.data.value?.playoff">
      <h2>Play-off</h2>
      <LoadState
        :loading="playoff.loading.value"
        :error="playoff.error.value"
      >
        <template v-if="playoff.data.value?.started">
          <section
            v-for="series in playoff.data.value.series"
            :key="series.key"
          >
            <h3>
              Seria {{ series.key }}:
              <template v-if="series.home && series.away">
                {{ series.home.name }} {{ series.home_wins }}:{{ series.away_wins }}
                {{ series.away.name }}
              </template>
              <span
                v-else
                class="meta"
              >czeka na wcześniejsze serie</span>
            </h3>
            <ul class="matches">
              <li
                v-for="match in series.matches"
                :key="match.id"
              >
                <RouterLink :to="{ name: 'admin-match', params: { slug, matchId: match.id } }">
                  <span class="teams">Mecz {{ match.round }}: {{ match.home.name }} – {{ match.away.name }}</span>
                  <span class="score">{{ score(match) || STATUS_LABELS[match.status] }}</span>
                </RouterLink>
              </li>
            </ul>
          </section>
        </template>
        <div
          v-else
          class="form"
        >
          <p class="meta">
            Format: {{ playoff.data.value?.format }}. Play-off można rozpocząć, gdy wszystkie
            mecze fazy zasadniczej są zakończone.
          </p>
          <button
            :disabled="starting.busy.value || !seasonOver"
            @click="startPlayoff"
          >
            Rozpocznij play-off
          </button>
          <p
            v-if="starting.error.value"
            class="error"
          >
            {{ starting.error.value }}
          </p>
        </div>
      </LoadState>
    </template>

    <h2>Terminarz</h2>
    <form
      v-if="!hasFixtures"
      class="form"
      @submit.prevent="generate"
    >
      <label class="check"><input
        v-model="double"
        type="checkbox"
      > mecz i rewanż</label>
      <button :disabled="generating.busy.value || (teams.data.value?.length ?? 0) < 2">
        Wygeneruj terminarz
      </button>
      <p
        v-if="generating.error.value"
        class="error"
      >
        {{ generating.error.value }}
      </p>
    </form>
    <section
      v-for="[round, list] in rounds"
      :key="round"
    >
      <h3>Kolejka {{ round }}</h3>
      <ul class="matches">
        <li
          v-for="match in list"
          :key="match.id"
        >
          <RouterLink :to="{ name: 'admin-match', params: { slug, matchId: match.id } }">
            <span class="teams">{{ match.home.name }} – {{ match.away.name }}</span>
            <span class="score">{{ score(match) || STATUS_LABELS[match.status] }}</span>
          </RouterLink>
        </li>
      </ul>
    </section>
  </LoadState>
</template>
