import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import CompetitionLayout from './views/CompetitionLayout.vue'
import CompetitionList from './views/CompetitionList.vue'
import MatchesView from './views/MatchesView.vue'
import MatchView from './views/MatchView.vue'
import RosterView from './views/RosterView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'
import TeamsView from './views/TeamsView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'competitions', component: CompetitionList },
  {
    path: '/competitions/:slug',
    component: CompetitionLayout,
    props: true,
    children: [
      { path: '', name: 'standings', component: StandingsView, props: true },
      { path: 'matches', name: 'matches', component: MatchesView, props: true },
      { path: 'teams', name: 'teams', component: TeamsView, props: true },
      { path: 'teams/:teamId', name: 'roster', component: RosterView, props: true },
      { path: 'stats', name: 'stats', component: StatsView, props: true },
      { path: 'matches/:matchId', name: 'match', component: MatchView, props: true },
    ],
  },
]

// Hash history (#/...): GitHub Pages serves static files only, so other paths would be 404s.
export const router = createRouter({ history: createWebHashHistory(), routes })
