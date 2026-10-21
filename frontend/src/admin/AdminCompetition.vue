<script setup lang="ts">
import { computed, reactive } from 'vue'
import { send } from '../api/client'
import { score, STATUS_LABELS } from '../api/format'
import type { CompetitionOut, MatchOut, TeamOut } from '../api/types'
import { useApi } from '../api/useApi'
import LoadState from '../components/LoadState.vue'
import { useAction } from './useAction'

const props = defineProps<{ slug: string }>()
const competition = useApi<CompetitionOut>(() => `competitions/${props.slug}`)
const teams = useApi<TeamOut[]>(() => `competitions/${props.slug}/teams`)
const matches = useApi<MatchOut[]>(() => `competitions/${props.slug}/matches`)
const savedTeams = useApi<TeamOut[]>(() => 'teams')

// Teams can be entered only until the fixtures are generated.
const hasFixtures = computed(() => (matches.data.value?.length ?? 0) > 0)
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

const double = reactive({ value: false })
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
    :loading="competition.loading.value"
    :error="competition.error.value"
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

    <h2>Terminarz</h2>
    <form
      v-if="!hasFixtures"
      class="form"
      @submit.prevent="generate"
    >
      <label class="check"><input
        v-model="double.value"
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
