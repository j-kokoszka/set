/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import './index.css'
import { parseBackendError } from './utils/error'
import { generateCodeVerifier, generateCodeChallenge, base64UrlDecode, type JwtPayload } from './utils/auth'
import FeedbackButton from './FeedbackButton'

interface Set {
  reps: number;
  weight: number;
  unit: 'kg' | 'lbs';
  difficulty?: 'easy' | 'moderate' | 'hard' | 'pass';
  completed?: boolean;
}

interface Exercise {
  id?: string;
  name: string;
  sets: Set[];
  progression?: ProgressionConfig;
}

interface StandardExercise {
  id: string;
  name: string;
  primaryMuscles: string[];
  secondaryMuscles?: string[];
  instructions?: string[];
  category: string;
  level?: string;
  force?: string;
  mechanic?: string;
  equipment?: string;
  is_external?: boolean;
}

const MUSCLE_GROUPS: Record<string, string[]> = {
  "Upper Body": ["chest", "shoulders", "biceps", "triceps", "forearms", "lats", "middle back", "traps", "lower back"],
  "Lower Body": ["quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors"],
  "Other": ["abdominals", "neck", "cardio"]
};

interface WorkoutHistoryItem {
  sk: string;
  name: string;
  exercises: {
    exercise_id?: string;
    exercise_name: string;
    sets: Set[];
  }[];
}

interface RoutineExerciseSet {
  reps?: number;
  weight?: number;
  unit: 'kg' | 'lbs';
}

interface ProgressionConfig {
  enabled: boolean;
  increment_weight: number;
  increment_reps: number;
  condition: 'all_completed' | 'last_set_completed';
}

interface RoutineExercise {
  exercise_id?: string;
  exercise_name: string;
  sets: RoutineExerciseSet[];
  progression?: ProgressionConfig;
}

interface WorkoutRoutine {
  id: string;
  name: string;
  exercises: RoutineExercise[];
}

interface Schedule {
  id: string;
  routine_id: string;
  routine_name?: string;
  schedule_type: 'recurring' | 'specific_date';
  day_of_week?: number;
  specific_date?: string;
}

interface PlannedWorkout {
  date: string;
  routine: WorkoutRoutine;
  is_recurring: boolean;
}

const KG_TO_LBS = 2.20462;
const BASE_URL = import.meta.env.VITE_API_URL || '/api';
const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN;
const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
const APP_URL = window.location.origin;

import { useTranslation } from 'react-i18next';
import i18n from './i18n';

function App() {
  const { t } = useTranslation();
  const [token, setToken] = useState<string | null>(localStorage.getItem('set_token'));
  const [user, setUser] = useState<string | null>(localStorage.getItem('set_user'));
  const [loginUsername, setLoginUsername] = useState('');

  const [view, setView] = useState<'workout' | 'routines' | 'plan'>('workout');
  const [workoutName, setWorkoutName] = useState(t('workout.new_workout', 'New Workout'));
  const [exercises, setExercises] = useState<Exercise[]>([]);

  // Sync default workout name on language change
  useEffect(() => {
    const enDefaults = ["New Workout", "New Routine"];
    const plDefaults = ["Nowy Trening", "Nowa Rutyna"];
    
    if (enDefaults.includes(workoutName) || plDefaults.includes(workoutName)) {
      // If it matches a routine default, use routine key, otherwise workout key
      if (workoutName.includes("Routine") || workoutName.includes("Rutyna")) {
        setWorkoutName(t('routines.new_routine', 'New Routine'));
      } else {
        setWorkoutName(t('workout.new_workout', 'New Workout'));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.language]);

  const [allExercises, setAllExercises] = useState<StandardExercise[]>([]);
  const [history, setHistory] = useState<WorkoutHistoryItem[]>([]);
  const [routines, setRoutines] = useState<WorkoutRoutine[]>([]);
  const [upcomingPlan, setUpcomingPlan] = useState<PlannedWorkout[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingExercises, setLoadingExercises] = useState(false);
  const [isLoadingExternal, setIsLoadingExternal] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [isCreatingCustom, setIsCreatingCustom] = useState(false);
  const [isSelectingRoutine, setIsSelectingRoutine] = useState(false);
  const [newExName, setNewExName] = useState("");
  const [customExName, setCustomExName] = useState("");
  const [customExMuscle, setCustomExMuscle] = useState("");
  const [customExCategory, setCustomExCategory] = useState("strength");
  const [customExLevel, setCustomExLevel] = useState("beginner");
  const [customExForce, setCustomExForce] = useState("");
  const [customExMechanic, setCustomExMechanic] = useState("");
  const [customExEquipment, setCustomExEquipment] = useState("");
  const [customExSecondaryMuscles, setCustomExSecondaryMuscles] = useState("");
  const [customExInstructions, setCustomExInstructions] = useState("");
  const [isLoadingSuggest, setIsLoadingSuggest] = useState(false);
  const [searchIndex, setSearchIndex] = useState(-1);
  const [editingWorkoutId, setEditingWorkoutId] = useState<string | null>(null);
  const [editingWorkoutDate, setEditingWorkoutDate] = useState<string | null>(null);
  const [editingRoutineId, setEditingRoutineId] = useState<string | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isScheduling, setIsScheduling] = useState(false);
  const [planSubView, setPlanSubView] = useState<'list' | 'calendar'>('list');
  const [calendarDate, setCalendarDate] = useState(new Date());
  
  // Scheduling state
  const [selectedRoutineId, setSelectedRoutineId] = useState("");
  const [scheduleType, setScheduleType] = useState<'recurring' | 'specific_date'>('recurring');
  const [selectedDay, setSelectedDay] = useState(0);
  const [selectedSpecificDate, setSelectedSpecificDate] = useState(new Date().toISOString().split('T')[0]);


  // Navigation state
  const [navPath, setNavPath] = useState<string[]>([]);

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('set_token');
    localStorage.removeItem('set_refresh_token');
    localStorage.removeItem('set_user');
    setView('workout');
  };

  const refreshPromise = useRef<Promise<string | null> | null>(null);

  const refreshIdToken = useCallback(async () => {
    if (refreshPromise.current) {
      return refreshPromise.current;
    }

    refreshPromise.current = (async () => {
      const refreshToken = localStorage.getItem('set_refresh_token');
      if (!refreshToken || !COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
        handleLogout();
        return null;
      }

      try {
        const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            grant_type: 'refresh_token',
            client_id: COGNITO_CLIENT_ID,
            refresh_token: refreshToken
          })
        });

        if (response.ok) {
          const data = await response.json();
          const newIdToken = data.id_token;
          const newRefreshToken = data.refresh_token;
          if (newIdToken) {
            setToken(newIdToken);
            localStorage.setItem('set_token', newIdToken);
            if (newRefreshToken) {
              localStorage.setItem('set_refresh_token', newRefreshToken);
            }
            return newIdToken;
          }
        } else {
          handleLogout();
        }
      } catch (e) {
        console.error('Failed to refresh token', e);
      } finally {
        refreshPromise.current = null;
      }
      return null;
    })();

    return refreshPromise.current;
  }, []);

  const getValidToken = useCallback(async () => {
    if (!token) return null;
    if (token.startsWith('mock_')) return token;

    const parts = token.split('.');
    if (parts.length !== 3) {
      handleLogout();
      return null;
    }

    const payload = base64UrlDecode(parts[1]);
    if (!payload || typeof payload.exp !== 'number') {
      handleLogout();
      return null;
    }

    const currentTime = Math.floor(Date.now() / 1000);
    // Refresh if expiring in less than 5 minutes
    if (payload.exp - currentTime < 300) {
      const newToken = await refreshIdToken();
      return newToken;
    }
    return token;
  }, [token, refreshIdToken]);

  const fetchExercises = useCallback(async () => {
    setLoadingExercises(true);
    try {
      // 1. Fetch built-in exercises
      const builtInResp = await fetch(`${BASE_URL}/exercises`);
      const builtInData = builtInResp.ok ? await builtInResp.json() : [];
      
      // 2. Fetch custom exercises if logged in
      let customData = [];
      const validToken = await getValidToken();
      if (validToken) {
        const customResp = await fetch(`${BASE_URL}/exercises/custom`, {
          headers: { 'Authorization': `Bearer ${validToken}` }
        });
        customData = customResp.ok ? await customResp.json() : [];
      }
      
      setAllExercises([...builtInData, ...customData]);
    } catch (error) {
      console.error('Error fetching exercises:', error);
      alert(t('exercises.database_load_error', 'Could not load exercise database. Some features may be limited.'));
    } finally {
      setLoadingExercises(false);
    }
  }, [getValidToken, t]);

  const filteredExercises = useMemo(() => {
    if (!newExName.trim()) return allExercises.slice(0, 15); // Show first 15 as default suggestions
    return allExercises.filter(ex => 
      ex.name.toLowerCase().includes(newExName.toLowerCase())
    ).slice(0, 10); // Limit search results to top 10 for performance
  }, [newExName, allExercises]);

  const navExercises = useMemo(() => {
    if (navPath.length < 2) return [];
    const muscle = navPath[1];
    return allExercises.filter(ex => ex.primaryMuscles.includes(muscle));
  }, [navPath, allExercises]);

  useEffect(() => {
    fetchExercises();
  }, [fetchExercises]);

  const fetchHistory = useCallback(async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/workouts`, {
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  }, [getValidToken]);

  const fetchRoutines = useCallback(async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/routines`, {
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRoutines(data);
      }
    } catch (error) {
      console.error('Error fetching routines:', error);
    } finally {
      setLoading(false);
    }
  }, [getValidToken]);

  const fetchPlan = useCallback(async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/plan/upcoming`, {
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUpcomingPlan(data);
      }
    } catch (error) {
      console.error('Error fetching plan:', error);
    } finally {
      setLoading(false);
    }
  }, [getValidToken]);

  const fetchSchedules = useCallback(async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    try {
      const response = await fetch(`${BASE_URL}/schedules`, {
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSchedules(data);
      }
    } catch (error) {
      console.error('Error fetching schedules:', error);
    }
  }, [getValidToken]);

  useEffect(() => {
    if (token) {
      fetchHistory();
      fetchRoutines();
      fetchPlan();
      fetchSchedules();
    }
  }, [token, fetchHistory, fetchRoutines, fetchPlan, fetchSchedules]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (loginUsername.trim()) {
      const mockToken = `mock_${loginUsername.trim()}`;
      setToken(mockToken);
      setUser(loginUsername.trim());
      localStorage.setItem('set_token', mockToken);
      localStorage.setItem('set_user', loginUsername.trim());
    }
  };

  const handleGoogleLogin = async () => {
    if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
      alert(t('app.sso_not_configured', 'Google SSO is not configured for this environment.'));
      return;
    }

    // Secure Authorization Code Flow with PKCE
    const codeVerifier = generateCodeVerifier();
    localStorage.setItem('set_code_verifier', codeVerifier);
    const codeChallenge = await generateCodeChallenge(codeVerifier);

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: COGNITO_CLIENT_ID,
      redirect_uri: APP_URL,
      scope: 'openid profile email',
      code_challenge_method: 'S256',
      code_challenge: codeChallenge,
      identity_provider: 'Google'
    });

    window.location.href = `https://${COGNITO_DOMAIN}/oauth2/authorize?${params.toString()}`;
  };

  useEffect(() => {
    const handleAuth = async () => {
      // 1. Check for 'code' in URL query (returning from Cognito with Auth Code Flow)
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      
      if (code) {
        const codeVerifier = localStorage.getItem('set_code_verifier');
        if (!codeVerifier) {
          console.error('No code verifier found');
          return;
        }

        try {
          const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
              grant_type: 'authorization_code',
              client_id: COGNITO_CLIENT_ID!,
              code: code,
              redirect_uri: APP_URL,
              code_verifier: codeVerifier
            })
          });

          if (response.ok) {
            const data = await response.json();
            const idToken = data.id_token;
            const refreshToken = data.refresh_token;
            
            // Extract user from ID Token (simple decode)
            const payload: JwtPayload | null = base64UrlDecode(idToken?.split('.')[1] || '');
            const username = payload ? (payload.name || payload.email || payload["cognito:username"]) : null;

            setToken(idToken);
            setUser(username || "Unknown");
            localStorage.setItem('set_token', idToken);
            if (refreshToken) {
              localStorage.setItem('set_refresh_token', refreshToken);
            }
            localStorage.setItem('set_user', username || "Unknown");
            
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        } catch (e) {
          console.error('Auth failed', e);
        }
      }
    };

    if (COGNITO_DOMAIN) {
      handleAuth();
    }
  }, []);

  const addExercise = (standardEx?: StandardExercise) => {
    const newEx: Exercise = {
      id: standardEx?.id,
      name: standardEx ? standardEx.name : newExName,
      sets: [{ reps: 0, weight: 0, unit: 'kg' }]
    };
    setExercises([...exercises, newEx]);
    setNewExName("");
    setIsAdding(false);
    setNavPath([]);
  };

  const removeExercise = (index: number) => {
    setExercises(exercises.filter((_, i) => i !== index));
  };

  const addSet = (exerciseIndex: number) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      const lastSet = ex.sets[ex.sets.length - 1];
      return {
        ...ex,
        sets: [...ex.sets, { 
          reps: lastSet?.reps || 0, 
          weight: lastSet?.weight || 0, 
          unit: lastSet?.unit || 'kg' 
        }]
      };
    }));
  };

  const removeSet = (exerciseIndex: number, setIndex: number) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      return {
        ...ex,
        sets: ex.sets.filter((_, sIdx) => sIdx !== setIndex)
      };
    }));
  };

  const updateSet = (exerciseIndex: number, setIndex: number, field: keyof Set, value: string | number | boolean) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      return {
        ...ex,
        sets: ex.sets.map((s, sIdx) => 
          sIdx === setIndex ? { ...s, [field]: value } : s
        )
      };
    }));
  };

  const updateProgression = (exerciseIndex: number, field: keyof ProgressionConfig, value: string | number | boolean) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      const currentProg = ex.progression || { enabled: false, increment_weight: 2.5, increment_reps: 0, condition: 'all_completed' };
      return {
        ...ex,
        progression: { ...currentProg, [field]: value }
      };
    }));
  };

  const startEdit = (workout: WorkoutHistoryItem) => {
    setWorkoutName(workout.name);
    setExercises(workout.exercises.map(ex => ({
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets
    })));
    setEditingWorkoutId(workout.sk.split('#')[2]);
    setEditingWorkoutDate(workout.sk.split('#')[1]);
    setView('workout');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const deleteWorkout = async (sk: string) => {
    const parts = sk.split('#');
    const date = parts[1];
    const workoutId = parts[2];

    if (!window.confirm(t('history.confirm_delete', 'Are you sure you want to delete this workout?'))) {
      return;
    }

    try {
      const validToken = await getValidToken();
      if (!validToken) return;

      const response = await fetch(`${BASE_URL}/workouts/${workoutId}?date=${encodeURIComponent(date)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        fetchHistory();
      } else {
        const errorMessage = await parseBackendError(response, t('workout.error_delete', 'Failed to delete workout'));
        alert(errorMessage);
      }
    } catch (error) {
      console.error('Error deleting workout:', error);
      alert(`Error connecting to backend: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const deleteRoutine = async (routineId: string) => {
    if (!window.confirm(t('routines.confirm_delete', 'Are you sure you want to delete this routine?'))) return;
    const validToken = await getValidToken();
    if (!validToken) return;

    try {
      const response = await fetch(`${BASE_URL}/routines/${routineId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        fetchRoutines();
      } else {
        const errorMessage = await parseBackendError(response, t('routines.error_delete', 'Error deleting routine'));
        alert(errorMessage);
      }
    } catch (e) {
      console.error('Error deleting routine:', e);
      const errorMessage = e instanceof Error ? e.message : t('common.unknown_error', 'An unknown error occurred');
      alert(`${t('routines.error_delete', 'Error deleting routine')}: ${errorMessage}`);
    }
  };

  const startFromPlanned = (planned: PlannedWorkout) => {
    setWorkoutName(planned.routine.name);
    setExercises(planned.routine.exercises.map(ex => ({
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets.map(s => ({
        reps: s.reps || 0,
        weight: s.weight || 0,
        unit: s.unit || 'kg'
      })),
      progression: ex.progression
    })));
    setView('workout');
  };

  const saveSchedule = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;

    const schedule: Partial<Schedule> = {
      routine_id: selectedRoutineId,
      schedule_type: scheduleType,
      day_of_week: scheduleType === 'recurring' ? selectedDay : undefined,
      specific_date: scheduleType === 'specific_date' ? selectedSpecificDate : undefined,
    };

    try {
      const response = await fetch(`${BASE_URL}/schedules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${validToken}`
        },
        body: JSON.stringify(schedule)
      });

      if (response.ok) {
        setIsScheduling(false);
        fetchSchedules();
        fetchPlan();
      } else {
        alert(t("plan.error_save", "Failed to save schedule"));
      }
    } catch (e) {
      console.error('Error saving schedule:', e);
    }
  };

  const deleteSchedule = async (scheduleId: string) => {
    if (!window.confirm(t("plan.confirm_delete", "Delete this schedule?"))) return;
    const validToken = await getValidToken();
    if (!validToken) return;

    try {
      const response = await fetch(`${BASE_URL}/schedules/${scheduleId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        fetchSchedules();
        fetchPlan();
      }
    } catch (e) {
      console.error('Error deleting schedule:', e);
    }
  };

  const renderCalendar = () => {
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    
    // Pre-group data by date for O(1) lookup in loop
    const historyByDate: Record<string, WorkoutHistoryItem[]> = {};
    history.forEach(w => {
      const date = w.sk.split('#')[1]?.split('T')[0];
      if (date) {
        if (!historyByDate[date]) historyByDate[date] = [];
        historyByDate[date].push(w);
      }
    });

    const planByDate: Record<string, PlannedWorkout[]> = {};
    upcomingPlan.forEach(p => {
      if (!planByDate[p.date]) planByDate[p.date] = [];
      planByDate[p.date].push(p);
    });

    const days = [];
    // Adjusted for Monday start (0=Mon, 6=Sun)
    const adjustedFirstDay = (firstDay + 6) % 7;
    
    for (let i = 0; i < adjustedFirstDay; i++) {
      days.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
    }
    
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const dayPlan = planByDate[dateStr] || [];
      const dayHistory = historyByDate[dateStr] || [];
      
      days.push(
        <div key={d} className="calendar-day">
          <span className="day-number">{d}</span>
          <div className="day-content">
            {dayHistory.map((w) => (
              <div key={w.sk} className="calendar-event completed" onClick={() => { setPlanSubView('list'); setIsMenuOpen(false); }}>
                {w.name} ✓
              </div>
            ))}
            {dayPlan.map((p) => (
              <div key={`${p.date}-${p.routine.id}`} className="calendar-event" onClick={() => startFromPlanned(p)}>
                {p.routine.name}
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    return (
      <div className="calendar">
        <div className="calendar-header">
          <button className="btn btn-small" onClick={() => setCalendarDate(new Date(year, month - 1))}>&lt;</button>
          <h3>{new Date(year, month).toLocaleString(i18n.resolvedLanguage, { month: 'long', year: 'numeric' })}</h3>
          <button className="btn btn-small" onClick={() => setCalendarDate(new Date(year, month + 1))}>&gt;</button>
        </div>
        <div className="calendar-grid">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
            <div key={day} className="calendar-weekday">{t(`common.days_short.${day.toLowerCase()}`, day)}</div>
          ))}
          {days}
        </div>
      </div>
    );
  };

  const startFromRoutine = (routine: WorkoutRoutine) => {
    setWorkoutName(routine.name);
    setExercises(routine.exercises.map(ex => ({
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets.map(s => ({
        reps: s.reps || 0,
        weight: s.weight || 0,
        unit: s.unit || 'kg'
      }))
    })));
    setIsSelectingRoutine(false);
  };

  const startRoutineEdit = (routine: WorkoutRoutine) => {
    setWorkoutName(routine.name);
    setExercises(routine.exercises.map(ex => ({
      id: ex.exercise_id,
      name: ex.exercise_name,
      sets: ex.sets.map(s => ({
        reps: s.reps || 0,
        weight: s.weight || 0,
        unit: s.unit || 'kg'
      }))
    })));
    setEditingRoutineId(routine.id);
    setView('workout');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const clearWorkout = () => {
    if (exercises.length === 0) return;
    if (window.confirm(t('workout.confirm_clear', 'Are you sure you want to clear all exercises from the current log?'))) {
      setExercises([]);
      setWorkoutName(t('workout.new_workout', 'New Workout'));
      setEditingWorkoutId(null);
      setEditingWorkoutDate(null);
      setEditingRoutineId(null);
    }
  };

  const searchExternal = async () => {
    if (!newExName.trim()) return;
    const validToken = await getValidToken();
    if (!validToken) {
      alert(t('exercises.login_required', 'Please log in to search the online database.'));
      return;
    }

    setIsLoadingExternal(true);
    try {
      const response = await fetch(`${BASE_URL}/exercises/search?q=${encodeURIComponent(newExName)}`, {
        headers: { 'Authorization': `Bearer ${validToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        // Merge with existing but prefer external
        setAllExercises(prev => {
          const combined = [...data, ...prev];
          const seen = new Set();
          return combined.filter(ex => {
            const duplicate = seen.has(ex.id);
            seen.add(ex.id);
            return !duplicate;
          });
        });
      }
    } catch (e) {
      console.error('External search failed', e);
    } finally {
      setIsLoadingExternal(false);
    }
  };

  const suggestCustomExercise = async () => {
    if (!customExName.trim()) return;
    const validToken = await getValidToken();
    if (!validToken) return;

    setIsLoadingSuggest(true);
    try {
      const response = await fetch(`${BASE_URL}/exercises/custom/suggest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${validToken}`
        },
        body: JSON.stringify({ name: customExName })
      });

      if (response.ok) {
        const data = await response.json();
        setCustomExMuscle(data.primaryMuscles?.join(', ') || "");
        setCustomExSecondaryMuscles(data.secondaryMuscles?.join(', ') || "");
        setCustomExCategory(data.category || "strength");
        setCustomExLevel(data.level || "beginner");
        setCustomExForce(data.force || "");
        setCustomExMechanic(data.mechanic || "");
        setCustomExEquipment(data.equipment || "");
        setCustomExInstructions(data.instructions?.join('\n') || "");
      }
    } catch (e) {
      console.error('Failed to get AI suggestions', e);
    } finally {
      setIsLoadingSuggest(false);
    }
  };

  const saveCustomExercise = async () => {
    if (!customExName.trim()) return;
    const validToken = await getValidToken();
    if (!validToken) return;

    try {
      const response = await fetch(`${BASE_URL}/exercises/custom`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${validToken}`
        },
        body: JSON.stringify({
          name: customExName,
          category: customExCategory,
          level: customExLevel,
          force: customExForce || undefined,
          mechanic: customExMechanic || undefined,
          equipment: customExEquipment || undefined,
          primaryMuscles: customExMuscle ? customExMuscle.split(',').map(m => m.trim()).filter(m => m) : [],
          secondaryMuscles: customExSecondaryMuscles ? customExSecondaryMuscles.split(',').map(m => m.trim()).filter(m => m) : [],
          instructions: customExInstructions ? customExInstructions.split('\n').map(i => i.trim()).filter(i => i) : []
        })
      });

      if (response.ok) {
        const newEx = await response.json();
        setAllExercises(prev => [...prev, newEx]);
        addExercise(newEx);
        setIsCreatingCustom(false);
        // Reset states
        setCustomExName("");
        setCustomExMuscle("");
        setCustomExSecondaryMuscles("");
        setCustomExCategory("strength");
        setCustomExLevel("beginner");
        setCustomExForce("");
        setCustomExMechanic("");
        setCustomExEquipment("");
        setCustomExInstructions("");
      }
    } catch (e) {
      console.error(t('custom_exercise.save_error', 'Failed to save custom exercise'), e);
      alert(t('custom_exercise.save_error', 'Failed to save custom exercise'));
    }
  };

  const toggleUnit = (exerciseIndex: number, setIndex: number) => {
    setExercises(prev => prev.map((ex, exIdx) => {
      if (exIdx !== exerciseIndex) return ex;
      return {
        ...ex,
        sets: ex.sets.map((s, sIdx) => {
          if (sIdx !== setIndex) return s;
          const currentUnit = s.unit || 'kg';
          const newUnit = currentUnit === 'kg' ? 'lbs' : 'kg';
          let newWeight = s.weight;
          if (newWeight > 0) {
            if (newUnit === 'lbs') {
              newWeight = Math.round(newWeight * KG_TO_LBS * 10) / 10;
            } else {
              newWeight = Math.round((newWeight / KG_TO_LBS) * 10) / 10;
            }
          }
          return { ...s, unit: newUnit, weight: newWeight };
        })
      };
    }));
  };

  const saveWorkout = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    interface WorkoutPayload {
      name: string;
      exercises: {
        exercise_id?: string;
        exercise_name: string;
        sets: Set[];
      }[];
      id?: string;
      date?: string | null;
    }

    const workout: WorkoutPayload = {
      name: workoutName,
      exercises: exercises.map(ex => ({
        exercise_id: ex.id,
        exercise_name: ex.name,
        sets: ex.sets
      })),
    };

    if (editingWorkoutId) {
      workout.id = editingWorkoutId;
      workout.date = editingWorkoutDate;
    }
    
    try {
      const url = editingWorkoutId 
        ? `${BASE_URL}/workouts/${editingWorkoutId}?old_date=${encodeURIComponent(editingWorkoutDate!)}`
        : `${BASE_URL}/workouts`;
      
      const response = await fetch(url, {
        method: editingWorkoutId ? 'PUT' : 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${validToken}`
        },
        body: JSON.stringify(workout),
      });
      
      if (response.ok) {
        alert(editingWorkoutId ? t('workout.updated_success', 'Workout updated!') : t('workout.saved_success', 'Workout saved!'));
        setExercises([]);
        setWorkoutName(t('workout.new_workout', 'New Workout'));
        setEditingWorkoutId(null);
        setEditingWorkoutDate(null);
        setView('plan');
        fetchHistory();
      } else {
        const errorMessage = await parseBackendError(response, t('workout.error_save', 'Failed to save workout'));
        alert(errorMessage);
      }
    } catch (e) {
      console.error('Error saving workout:', e);
      alert(`Error connecting to backend: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
  };

  const saveRoutine = async () => {
    const validToken = await getValidToken();
    if (!validToken) return;
    const routine: Partial<WorkoutRoutine> = {
      name: workoutName,
      exercises: exercises.map(ex => ({
        exercise_id: ex.id,
        exercise_name: ex.name,
        sets: ex.sets.map(s => ({
          reps: s.reps,
          weight: s.weight,
          unit: s.unit
        }))
      }))
    };

    if (editingRoutineId) routine.id = editingRoutineId;

    try {
      const response = await fetch(`${BASE_URL}/routines${editingRoutineId ? `/${editingRoutineId}` : ''}`, {
        method: editingRoutineId ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${validToken}`
        },
        body: JSON.stringify(routine)
      });
      if (response.ok) {
        alert(editingRoutineId ? t('routines.updated_success', 'Routine updated!') : t('routines.saved_success', 'Routine saved!'));
        setEditingRoutineId(null);
        setWorkoutName(t('workout.new_workout', 'New Workout'));
        setExercises([]);
        setView('routines');
        fetchRoutines();
      } else {
        const errorMessage = await parseBackendError(response, t('routines.error_save', 'Failed to save routine'));
        alert(errorMessage);
      }
    } catch (e) {
      console.error('Error saving routine:', e);
      alert(t('routines.error_save', 'Error saving routine'));
    }
  };

  if (!token) {
    return (
      <div className="login-container">
        <div className="card login-card">
          <h1 className="login-title">{t("app.title", "set")}</h1>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <button 
              className="btn" 
              onClick={handleGoogleLogin}
              style={{ 
                background: 'white', 
                color: '#3c4043', 
                border: '1px solid #dadce0',
              }}
            >
              <img src="https://www.gstatic.com/images/branding/product/1x/gsa_512dp.png" alt="Google" style={{ width: '20px', height: '20px' }} />
              {t("app.login_google", "Sign in with Google")}
            </button>

            {(import.meta.env.DEV || import.meta.env.VITE_ENABLE_MOCK_LOGIN === 'true') && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '0.5rem 0' }}>
                  <div style={{ flex: 1, height: '1px', background: 'var(--border-color)' }}></div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t("app.or_mock_login", "or mock login")}</span>
                  <div style={{ flex: 1, height: '1px', background: 'var(--border-color)' }}></div>
                </div>

                <form onSubmit={handleLogin}>
                  <div className="set-input-group mb-1">
                    <label htmlFor="username" className="set-input-label">{t("app.username", "Username")}</label>
                    <input 
                      id="username"
                      type="text" 
                      value={loginUsername}
                      onChange={(e) => setLoginUsername(e.target.value)}
                      placeholder={t("app.username_placeholder", "Enter your username")}
                      required
                    />
                  </div>
                  <button className="btn btn-secondary" type="submit">
                    Mock Login
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header>
        <div className="header-brand">
          <h1>{t("app.title", "set")}</h1>
          <div className="lang-switcher" style={{ display: 'flex', gap: '0.25rem', marginLeft: '0.5rem' }}>
            <button 
              className={`btn btn-small ${i18n.language === 'en' ? '' : 'btn-secondary'}`}
              onClick={() => i18n.changeLanguage('en')}
              style={{ padding: '0.1rem 0.4rem', fontSize: '0.6rem', height: 'auto' }}
            >
              EN
            </button>
            <button 
              className={`btn btn-small ${i18n.language.startsWith('pl') ? '' : 'btn-secondary'}`}
              onClick={() => i18n.changeLanguage('pl')}
              style={{ padding: '0.1rem 0.4rem', fontSize: '0.6rem', height: 'auto' }}
            >
              PL
            </button>
          </div>
          <span className="user-tag">{user}</span>
        </div>

        <button className="hamburger" onClick={() => setIsMenuOpen(!isMenuOpen)} aria-label="Toggle menu">
          {isMenuOpen ? '✕' : '☰'}
        </button>

        <div className={`nav-menu ${isMenuOpen ? 'open' : ''}`}>
          <button 
            className={`btn btn-small ${view === 'workout' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('workout'); setIsMenuOpen(false); }}
          >
            {t("workout.title", "Log")}
          </button>
          <button 
            className={`btn btn-small ${view === 'routines' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('routines'); setIsMenuOpen(false); }}
          >
            {t("routines.title", "Routines")}
          </button>
          <button 
            className={`btn btn-small ${view === 'plan' ? '' : 'btn-secondary'}`} 
            onClick={() => { setView('plan'); setIsMenuOpen(false); }}
          >
            {t("plan.title", "Plan")}
          </button>
          <button 
            className="btn btn-secondary btn-small" 
            onClick={() => { handleLogout(); setIsMenuOpen(false); }} 
            title={t("app.sign_out", "Sign Out")}
          >
            {t("app.logout", "Logout")}
          </button>
        </div>
      </header>

      {view === 'workout' ? (
        <div className="card">
          <div className="workout-header">
            <input 
              className="workout-name-input"
              value={workoutName} 
              onChange={(e) => setWorkoutName(e.target.value)} 
              placeholder={t("workout.workout_name_placeholder", "Workout Name")}
            />
            {!editingWorkoutId && !editingRoutineId && (
              <button 
                className="btn btn-secondary btn-small" 
                style={{ width: 'auto' }}
                onClick={() => setIsSelectingRoutine(true)}
              >
                {t("routines.start_from_routine", "Start from Routine")}
              </button>
            )}
          </div>

          {isSelectingRoutine && (
            <div className="modal-overlay" onClick={() => setIsSelectingRoutine(false)}>
              <div className="modal-content" onClick={e => e.stopPropagation()}>
                <h3 className="modal-title">{t("routines.select_routine", "Select a Routine")}</h3>
                {routines.length === 0 ? (
                  <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1rem' }}>{t("routines.no_routines_found", "No routines found. Create one in the Routines tab!")}</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
                    {routines.map(p => (
                      <button key={p.id} className="btn btn-secondary" style={{ textAlign: 'left', justifyContent: 'flex-start' }} onClick={() => startFromRoutine(p)}>
                        {p.name}
                      </button>
                    ))}
                  </div>
                )}
                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={() => setIsSelectingRoutine(false)}>{t("common.cancel", "Cancel")}</button>
                </div>
              </div>
            </div>
          )}
          
          <div className="workout-grid">
            {exercises.map((ex, exIdx) => (
              <div key={exIdx} className="exercise-row">
                <div className="exercise-header">
                  <div className="exercise-title">
                    <span>{ex.name}</span>
                    <button 
                      className="btn-danger"
                      onClick={() => removeExercise(exIdx)}
                      title={t("workout.remove_exercise", "Remove exercise")}
                    >
                      ✕
                    </button>
                  </div>
                  <button className="btn btn-secondary btn-small" onClick={() => addSet(exIdx)}>
                    {t("workout.add_set", "+ Set")}
                  </button>
                </div>

                {/* Progression Config */}
                <div className="progression-config-row" style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                  <div className="flex-between">
                    <div className="flex-center">
                      <input 
                        type="checkbox" 
                        id={`prog-enable-${exIdx}`}
                        checked={ex.progression?.enabled || false}
                        onChange={(e) => updateProgression(exIdx, 'enabled', e.target.checked)}
                        style={{ width: 'auto', marginRight: '0.5rem' }}
                      />
                      <label htmlFor={`prog-enable-${exIdx}`} style={{ fontSize: '0.85rem', fontWeight: 600 }}>{t("plan.enable_progression", "Auto Progression")}</label>
                    </div>
                    {ex.progression?.enabled && (
                      <div className="flex-center" style={{ gap: '1rem' }}>
                        <div className="set-input-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="set-input-label">+{t("workout.weight", "Weight")}</span>
                          <input 
                            type="number" 
                            step="0.5"
                            value={ex.progression.increment_weight} 
                            onChange={(e) => {
                              const val = parseFloat(e.target.value);
                              if (!isNaN(val)) updateProgression(exIdx, 'increment_weight', val);
                            }}
                            style={{ width: '60px', padding: '0.2rem' }}
                          />
                        </div>
                        <div className="set-input-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="set-input-label">+{t("workout.reps", "Reps")}</span>
                          <input 
                            type="number" 
                            value={ex.progression.increment_reps} 
                            onChange={(e) => {
                              const val = parseInt(e.target.value);
                              if (!isNaN(val)) updateProgression(exIdx, 'increment_reps', val);
                            }}
                            style={{ width: '50px', padding: '0.2rem' }}
                          />
                        </div>
                        <select 
                          value={ex.progression.condition} 
                          onChange={(e) => updateProgression(exIdx, 'condition', e.target.value)}
                          style={{ fontSize: '0.75rem', padding: '0.2rem' }}
                        >
                          <option value="all_completed">{t("plan.cond_all", "All Sets")}</option>
                          <option value="last_set_completed">{t("plan.cond_last", "Last Set")}</option>
                        </select>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="set-list">
                  {ex.sets.map((set, sIdx) => (
                    <div key={sIdx} className={`set-item ${set.completed ? 'completed' : ''}`}>
                      <div className="set-header">
                        <div className="flex-center">
                          <span className="set-label">{t("workout.set", "SET")} {sIdx + 1}</span>
                          {set.completed && <span style={{ color: 'var(--success-color)', fontSize: '0.9rem' }}>✓</span>}
                        </div>
                        <div className="flex-center">
                          <button 
                            className="btn-secondary btn-small"
                            onClick={() => updateSet(exIdx, sIdx, 'completed', !set.completed)}
                            style={{ fontSize: '0.65rem', padding: '0.2rem 0.5rem' }}
                          >
                            {set.completed ? t('common.undo', 'Undo') : t('common.done', 'Done')}
                          </button>
                          <button 
                            className="btn-danger"
                            onClick={() => removeSet(exIdx, sIdx)}
                            style={{ padding: '2px 4px', fontSize: '0.7rem' }}
                            title={t("workout.remove_set", "Remove set")}
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                      
                      <div className="set-input-row">
                        <div className="set-input-group">
                          <label className="set-input-label">{t("workout.weight", "Weight")}</label>
                          <div className="input-with-badge">
                            <input 
                              type="number" 
                              value={set.weight || ''} 
                              placeholder="0"
                              onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                if (!isNaN(val)) updateSet(exIdx, sIdx, 'weight', val);
                              }} 
                              style={{ paddingRight: '2.8rem' }}
                            />
                            <button 
                              className="unit-badge" 
                              onClick={() => toggleUnit(exIdx, sIdx)}
                            >
                              {t(`workout.unit.${set.unit || 'kg'}`, set.unit || 'kg')}
                            </button>
                          </div>
                        </div>
                        
                        <div className="set-input-group">
                          <label className="set-input-label">{t("workout.reps", "Reps")}</label>
                          <input 
                            type="number" 
                            value={set.reps || ''} 
                            placeholder="0"
                            onChange={(e) => {
                              const val = parseInt(e.target.value);
                              if (!isNaN(val)) updateSet(exIdx, sIdx, 'reps', val);
                            }} 
                          />
                        </div>
                      </div>

                      <div className="difficulty-row">
                        {([
                          { id: 'pass', icon: '⚪' },
                          { id: 'easy', icon: '🟢' },
                          { id: 'moderate', icon: '🟡' },
                          { id: 'hard', icon: '🔴' }
                        ] as const).map(diff => (
                          <button
                            key={diff.id}
                            className={`difficulty-btn ${set.difficulty === diff.id ? 'active' : ''}`}
                            data-diff={diff.id}
                            onClick={() => updateSet(exIdx, sIdx, 'difficulty', diff.id)}
                          >
                            <span className="difficulty-icon">{diff.icon}</span>
                            <span>{t('difficulty.' + diff.id, diff.id)}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {!isAdding ? (
            <button 
              className="btn btn-secondary" 
              style={{ border: '1px dashed var(--border-color)', marginTop: '1.5rem', background: 'transparent' }} 
              onClick={() => setIsAdding(true)}
            >
              {t("workout.add_exercise", "+ Add Exercise")}
            </button>
          ) : (
            <div className="card" style={{ marginTop: '1.5rem', border: '1px solid var(--primary-color)', padding: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <button 
                    className="btn btn-secondary btn-small" 
                    onClick={() => {
                      if (navPath.length > 0) {
                        setNavPath(navPath.slice(0, -1));
                      } else {
                        setIsAdding(false);
                      }
                    }}
                  >
                    {navPath.length > 0 ? t('common.back', '← Back') : t('common.cancel', 'Cancel')}
                  </button>
                  <span style={{ fontSize: '1rem', fontWeight: '700' }}>
                    {navPath.length === 0 ? t('exercises.select_category', 'Select Category') : navPath.map(p => t('muscles.' + p, p)).join(' / ')}
                  </span>
                </div>
              </div>


              {loadingExercises ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  {t("exercises.loading", "Loading exercise database...")}
                </div>
              ) : (
                <>
                  {newExName.trim() !== "" && (
                    <div style={{ marginBottom: '1rem' }}>
                      <input 
                        autoFocus
                        placeholder={t("exercises.search", "Search exercise...")}
                        value={newExName}
                        onChange={(e) => {
                          setNewExName(e.target.value);
                          setSearchIndex(-1);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            if (searchIndex >= 0 && searchIndex < filteredExercises.length) {
                              addExercise(filteredExercises[searchIndex]);
                            } else if (newExName.trim()) {
                              addExercise();
                            }
                          } else if (e.key === 'ArrowDown') {
                            e.preventDefault();
                            setSearchIndex(prev => Math.min(prev + 1, filteredExercises.length - 1));
                          } else if (e.key === 'ArrowUp') {
                            e.preventDefault();
                            setSearchIndex(prev => Math.max(prev - 1, -1));
                          } else if (e.key === 'Escape') {
                            setIsAdding(false);
                          }
                        }}
                      />
                      <div className="exercise-suggestions" style={{ position: 'static', marginTop: '0.5rem' }}>
                        {filteredExercises.length > 0 ? (
                          <>
                            {filteredExercises.map((ex, i) => (
                              <div 
                                key={ex.id} 
                                className={`suggestion-item ${i === searchIndex ? 'active' : ''}`}
                                onClick={() => addExercise(ex)}
                                onMouseEnter={() => setSearchIndex(i)}
                              >
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                  <span style={{ fontWeight: '600' }}>{ex.name} {ex.is_external && <small style={{ color: 'var(--primary-color)', marginLeft: '0.5rem' }}>{t("exercises.online_label", "[Online]")}</small>}</span>
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ex.primaryMuscles?.map(m => t('muscles.' + m, m)).join(', ')}</span>
                                </div>
                              </div>
                            ))}
                            <div className="suggestion-item" onClick={searchExternal} style={{ borderTop: '1px solid var(--border-color)', color: 'var(--primary-color)' }}>
                              {isLoadingExternal ? t("exercises.searching", "Searching...") : t("exercises.search_online", "🔍 Search in Online Database")}
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="suggestion-item" onClick={searchExternal}>
                              {isLoadingExternal ? t("exercises.searching", "Searching...") : t("exercises.search_online_query", '🔍 Search "{{query}}" online', { query: newExName })}
                            </div>
                            <div 
                              className="suggestion-item" 
                              onClick={() => { setCustomExName(newExName); setIsCreatingCustom(true); }}
                              style={{ color: 'var(--success-color)' }}
                            >
                              {t("exercises.create_custom", '➕ Create Custom: "{{query}}"', { query: newExName })}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {newExName.trim() === "" && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', maxHeight: '350px', overflowY: 'auto', padding: '0.25rem' }}>
                      {navPath.length === 0 && (
                        <div style={{ gridColumn: 'span 2', marginBottom: '1rem' }}>
                          <input 
                            autoFocus
                            placeholder={t("exercises.search", "Search exercise...")}
                            value={newExName}
                            onChange={(e) => {
                              setNewExName(e.target.value);
                              setSearchIndex(-1);
                            }}
                          />
                        </div>
                      )}

                      {navPath.length === 0 && Object.keys(MUSCLE_GROUPS).map(group => (
                        <button key={group} className="btn btn-secondary" onClick={() => setNavPath([group])}>
                          {t('muscles.' + group, group)}
                        </button>
                      ))}
                      
                      {navPath.length === 1 && MUSCLE_GROUPS[navPath[0]].map(muscle => (
                        <button key={muscle} className="btn btn-secondary" onClick={() => setNavPath([...navPath, muscle])} style={{ textTransform: 'capitalize' }}>
                          {t('muscles.' + muscle, muscle)}
                        </button>
                      ))}

                      {navPath.length === 2 && (
                        navExercises.length === 0 ? (
                          <div style={{ gridColumn: 'span 2', textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                            {t("exercises.no_exercises_found", "No exercises found for this muscle group.")}
                          </div>
                        ) : (
                          navExercises.map(ex => (
                            <button key={ex.id} className="btn btn-secondary" onClick={() => { addExercise(ex); setNavPath([]); }} style={{ fontSize: '0.85rem', textAlign: 'left', height: 'auto', padding: '0.75rem', justifyContent: 'flex-start' }}>
                              {ex.name}
                            </button>
                          ))
                        )
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          
          <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
            {exercises.length > 0 && (
              <>
                <button 
                  className="btn" 
                  style={{ flex: 2, background: 'var(--success-color)' }} 
                  onClick={saveWorkout}
                >
                  {editingWorkoutId ? t('workout.update_workout', 'Update Workout') : t('workout.save_workout', 'Save Workout')}
                </button>
                <button 
                  className="btn btn-secondary" 
                  style={{ flex: 1, color: 'var(--danger-color)', borderColor: 'var(--danger-color)' }} 
                  onClick={clearWorkout}
                >
                  {t("workout.clear", "Clear")}
                </button>
              </>
            )}
            {exercises.length > 0 && !editingWorkoutId && (
              <button 
                className="btn btn-secondary" 
                style={{ flex: 1 }} 
                onClick={saveRoutine}
              >
                {editingRoutineId ? t('routines.update_routine', 'Update Routine') : t('routines.save_as_routine', 'Save as Routine')}
              </button>
            )}
          </div>
        </div>
      ) : view === 'plan' ? (
        <div className="plan-view">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2 className="modal-title" style={{ margin: 0 }}>{t("plan.title", "Workout Plan")}</h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className={`btn btn-small ${planSubView === 'list' ? '' : 'btn-secondary'}`}
                onClick={() => setPlanSubView('list')}
              >
                {t("plan.list_view", "List")}
              </button>
              <button 
                className={`btn btn-small ${planSubView === 'calendar' ? '' : 'btn-secondary'}`}
                onClick={() => setPlanSubView('calendar')}
              >
                {t("plan.calendar_view", "Calendar")}
              </button>
              <button className="btn btn-small" onClick={() => setIsScheduling(true)}>
                {t("plan.schedule_btn", "Schedule Routine")}
              </button>
            </div>
          </div>

          {loading ? (
            <p style={{ textAlign: 'center', padding: '2rem' }}>{t("plan.loading", "Loading plan...")}</p>
          ) : planSubView === 'list' ? (
            <div className="plan-list">
              {/* Active Schedules Section */}
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem', textTransform: 'uppercase' }}>{t("plan.active_schedules", "Your Schedules")}</h3>
                {schedules.length === 0 ? (
                   <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{t("plan.no_schedules", "No recurring schedules set.")}</p>
                ) : (
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {schedules.map(s => (
                      <div key={s.id} className="tag" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {s.routine_name} ({s.schedule_type === 'recurring' ? t(`common.days_short.${['mon','tue','wed','thu','fri','sat','sun'][s.day_of_week!]}`) : s.specific_date})
                        <button 
                          className="btn-danger" 
                          style={{ padding: 0, fontSize: '0.6rem', border: 'none', background: 'transparent', cursor: 'pointer' }} 
                          onClick={() => deleteSchedule(s.id)}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem', textTransform: 'uppercase' }}>{t("plan.timeline", "Timeline")}</h3>
              
              {/* Unified Timeline: History + Upcoming Plan */}
              {(() => {
                const timelineItems = [
                  ...history.map(w => ({ type: 'history' as const, date: w.sk.split('#')[1], data: w })),
                  ...upcomingPlan.map(p => ({ type: 'plan' as const, date: p.date, data: p }))
                ].sort((a, b) => b.date.localeCompare(a.date));

                if (timelineItems.length === 0) {
                  return <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '4rem' }}>{t("plan.no_activity", "No activity or upcoming workouts.")}</p>;
                }

                return timelineItems.map((item) => {
                  if (item.type === 'history') {
                    const w = item.data as WorkoutHistoryItem;
                    return (
                      <div key={w.sk} className="card history-item" style={{ borderLeft: '4px solid var(--success-color)' }}>
                        <div className="item-header">
                          <div className="item-title">
                            <span className="item-name">{w.name} ✓</span>
                            <span className="item-meta">
                              {new Date(w.sk.split('#')[1]).toLocaleDateString(i18n.resolvedLanguage, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '0.25rem' }}>
                            <button 
                              className="btn-secondary btn-small"
                              onClick={() => startEdit(w)}
                              title={t("history.edit_workout", "Edit workout")}
                            >
                              ✎
                            </button>
                            <button 
                              className="btn-danger btn-small"
                              onClick={() => deleteWorkout(w.sk)}
                              title={t("history.delete_workout", "Delete workout")}
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                        <div className="tag-list">
                          {w.exercises?.map((ex, eIdx: number) => (
                            <span key={eIdx} className="tag">
                              {ex.exercise_name} ({ex.sets?.length})
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  } else {
                    const p = item.data as PlannedWorkout;
                    return (
                      <div key={`${p.date}-${p.routine.id}`} className="card plan-item">
                        <div className="item-header">
                          <div className="item-title">
                            <span className="item-name">{p.routine.name}</span>
                            <span className="item-meta">
                              {new Date(p.date).toLocaleDateString(i18n.resolvedLanguage, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                              {p.is_recurring && <span className="tag" style={{ marginLeft: '0.5rem' }}>{t("plan.recurring", "Recurring")}</span>}
                            </span>
                          </div>
                          <button className="btn btn-small" onClick={() => startFromPlanned(p)}>
                            {t("plan.start_workout", "Start")}
                          </button>
                        </div>
                        <div className="tag-list">
                          {p.routine.exercises.map((ex, eIdx) => (
                            <span key={eIdx} className="tag">
                              {ex.exercise_name} ({ex.sets.length} sets, {ex.sets[0]?.weight}{ex.sets[0]?.unit})
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  }
                });
              })()}
            </div>
          ) : (
            <div className="calendar-container card">
              {renderCalendar()}
            </div>
          )}
        </div>
      ) : (
        <div className="routines-list">
          {loading ? (
            <p style={{ textAlign: 'center', padding: '2rem' }}>{t("routines.loading", "Loading routines...")}</p>
          ) : routines.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>{t("routines.no_routines", "No routines found. Templates help you start workouts faster!")}</p>
              <button className="btn" style={{ width: 'auto' }} onClick={() => { setView('workout'); setWorkoutName(t('routines.new_routine', 'New Routine')); setExercises([]); setEditingWorkoutId(null); setEditingWorkoutDate(null); setEditingRoutineId(null); }}>
                {t("routines.create_first", "Create My First Routine")}
              </button>
            </div>
          ) : (
            <>
              <button 
                className="btn btn-secondary" 
                style={{ marginBottom: '1.5rem', border: '1px dashed var(--border-color)', background: 'transparent' }}
                onClick={() => { setView('workout'); setWorkoutName(t('routines.new_routine', 'New Routine')); setExercises([]); setEditingWorkoutId(null); setEditingWorkoutDate(null); setEditingRoutineId(null); }}
              >
                {t("routines.create_new", "+ Create New Routine")}
              </button>
              {routines.map((p) => (
              <div key={p.id} className="card routine-item">
                <div className="item-header">
                  <div className="item-title">
                    <span className="item-name">{p.name}</span>
                    <span className="item-meta">{p.exercises.length}{t("routines.exercises_count", " exercises")}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button 
                      className="btn btn-small" 
                      onClick={() => startFromRoutine(p)}
                    >
                      {t("routines.use", "Use")}
                    </button>
                    <button 
                      className="btn-secondary btn-small"
                      onClick={() => startRoutineEdit(p)}
                      title={t("routines.edit_routine", "Edit routine")}
                    >
                      ✎
                    </button>
                    <button 
                      className="btn-danger btn-small"
                      onClick={() => deleteRoutine(p.id)}
                      title={t("routines.delete_routine", "Delete routine")}
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div className="tag-list">
                  {p.exercises.map((ex, eIdx) => (
                    <span key={eIdx} className="tag">
                      {ex.exercise_name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            </>
          )}
        </div>
      )}

      {isCreatingCustom && (
        <div className="modal-overlay" onClick={() => setIsCreatingCustom(false)}>
          <div className="modal-content" style={{ maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 className="modal-title" style={{ margin: 0 }}>{t("custom_exercise.title", "Create Custom Exercise")}</h3>
              <button 
                className="btn btn-secondary btn-small"
                onClick={suggestCustomExercise}
                disabled={!customExName || isLoadingSuggest}
                style={{ background: 'var(--primary-color)', color: 'white', border: 'none' }}
              >
                {isLoadingSuggest ? t("custom_exercise.generating", "Generating...") : t("custom_exercise.autofill", "✨ Auto-fill with AI")}
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
              {t("custom_exercise.instruction_text", "Fill in the details below or use AI to generate them based on the name.")}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '2rem' }}>
              <div className="set-input-group">
                <label className="set-input-label" htmlFor="custom-ex-name">{t("custom_exercise.name", "Exercise Name")}</label>
                <input 
                  id="custom-ex-name"
                  autoFocus
                  value={customExName} 
                  onChange={e => setCustomExName(e.target.value)} 
                  placeholder={t("custom_exercise.placeholder_name", "e.g. Weighted Pullups")}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="set-input-group">
                  <label className="set-input-label" htmlFor="custom-ex-category">{t("custom_exercise.category", "Category")}</label>
                  <select id="custom-ex-category" value={customExCategory} onChange={e => setCustomExCategory(e.target.value)}>
                    <option value="strength">{t("category.strength", "Strength")}</option>
                    <option value="cardio">{t("category.cardio", "Cardio")}</option>
                    <option value="stretching">{t("category.stretching", "Stretching")}</option>
                    <option value="plyometrics">{t("category.plyometrics", "Plyometrics")}</option>
                  </select>
                </div>
                <div className="set-input-group">
                  <label className="set-input-label" htmlFor="custom-ex-level">{t("custom_exercise.level", "Level")}</label>
                  <select id="custom-ex-level" value={customExLevel} onChange={e => setCustomExLevel(e.target.value)}>
                    <option value="beginner">{t("difficulty.beginner", "Beginner")}</option>
                    <option value="intermediate">{t("difficulty.intermediate", "Intermediate")}</option>
                    <option value="expert">{t("difficulty.expert", "Expert")}</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="set-input-group">
                  <label className="set-input-label" htmlFor="custom-ex-force">{t("custom_exercise.force", "Force")}</label>
                  <select id="custom-ex-force" value={customExForce} onChange={e => setCustomExForce(e.target.value)}>
                    <option value="">{t("common.select_prompt", "Select...")}</option>
                    <option value="push">{t("force.push", "Push")}</option>
                    <option value="pull">{t("force.pull", "Pull")}</option>
                    <option value="static">{t("force.static", "Static")}</option>
                  </select>
                </div>
                <div className="set-input-group">
                  <label className="set-input-label" htmlFor="custom-ex-mechanic">{t("custom_exercise.mechanic", "Mechanic")}</label>
                  <select id="custom-ex-mechanic" value={customExMechanic} onChange={e => setCustomExMechanic(e.target.value)}>
                    <option value="">{t("common.select_prompt", "Select...")}</option>
                    <option value="compound">{t("mechanic.compound", "Compound")}</option>
                    <option value="isolation">{t("mechanic.isolation", "Isolation")}</option>
                  </select>
                </div>
              </div>

              <div className="set-input-group">
                <label className="set-input-label" htmlFor="custom-ex-equipment">{t("custom_exercise.equipment", "Equipment")}</label>
                <input 
                  id="custom-ex-equipment"
                  value={customExEquipment} 
                  onChange={e => setCustomExEquipment(e.target.value)} 
                  placeholder={t("custom_exercise.placeholder_equipment", "e.g. barbell, dumbbell, machine")}
                />
              </div>

              <div className="set-input-group">
                <label className="set-input-label" htmlFor="custom-ex-primary">{t("custom_exercise.primary_muscles", "Primary Muscles")}</label>
                <input 
                  id="custom-ex-primary"
                  value={customExMuscle} 
                  onChange={e => setCustomExMuscle(e.target.value)} 
                  placeholder={t("custom_exercise.placeholder_muscles", "e.g. chest, shoulders (comma separated)")}
                />
              </div>

              <div className="set-input-group">
                <label className="set-input-label" htmlFor="custom-ex-secondary">{t("custom_exercise.secondary_muscles", "Secondary Muscles")}</label>
                <input 
                  id="custom-ex-secondary"
                  value={customExSecondaryMuscles} 
                  onChange={e => setCustomExSecondaryMuscles(e.target.value)} 
                  placeholder={t("custom_exercise.placeholder_muscles", "e.g. triceps (comma separated)")}
                />
              </div>

              <div className="set-input-group">
                <label className="set-input-label" htmlFor="custom-ex-instructions">{t("custom_exercise.instructions", "Instructions")}</label>
                <textarea 
                  id="custom-ex-instructions"
                  value={customExInstructions} 
                  onChange={e => setCustomExInstructions(e.target.value)} 
                  placeholder={t("custom_exercise.placeholder_instructions", "Enter each step on a new line")}
                  rows={4}
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', resize: 'vertical' }}
                />
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setIsCreatingCustom(false)}>{t("common.cancel", "Cancel")}</button>
              <button className="btn" onClick={saveCustomExercise}>{t("custom_exercise.save_and_add", "Save & Add")}</button>
            </div>
          </div>
        </div>
      )}

      <FeedbackButton getValidToken={getValidToken} />

      {isScheduling && (
        <div className="modal-overlay" onClick={() => setIsScheduling(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">{t("plan.schedule_modal_title", "Schedule a Routine")}</h3>
            
            <div className="set-input-group mb-1">
              <label className="set-input-label">{t("plan.select_routine", "Routine")}</label>
              <select value={selectedRoutineId} onChange={e => setSelectedRoutineId(e.target.value)}>
                <option value="">{t("common.select_prompt", "Select...")}</option>
                {routines.map(r => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>

            <div className="set-input-group mb-1">
              <label className="set-input-label">{t("plan.schedule_type", "Schedule Type")}</label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button 
                  className={`btn btn-small ${scheduleType === 'recurring' ? '' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                  onClick={() => setScheduleType('recurring')}
                >
                  {t("plan.recurring", "Recurring")}
                </button>
                <button 
                  className={`btn btn-small ${scheduleType === 'specific_date' ? '' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                  onClick={() => setScheduleType('specific_date')}
                >
                  {t("plan.specific_date", "Specific Date")}
                </button>
              </div>
            </div>

            {scheduleType === 'recurring' ? (
              <div className="set-input-group mb-1">
                <label className="set-input-label">{t("plan.day_of_week", "Day of Week")}</label>
                <select value={selectedDay} onChange={e => {
                  const val = parseInt(e.target.value);
                  if (!isNaN(val)) setSelectedDay(val);
                }}>
                  {[
                    { val: 0, label: 'Monday' },
                    { val: 1, label: 'Tuesday' },
                    { val: 2, label: 'Wednesday' },
                    { val: 3, label: 'Thursday' },
                    { val: 4, label: 'Friday' },
                    { val: 5, label: 'Saturday' },
                    { val: 6, label: 'Sunday' }
                  ].map(d => (
                    <option key={d.val} value={d.val}>{t(`common.days.${d.label.toLowerCase()}`, d.label)}</option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="set-input-group mb-1">
                <label className="set-input-label">{t("plan.date", "Date")}</label>
                <input 
                  type="date" 
                  value={selectedSpecificDate} 
                  onChange={e => setSelectedSpecificDate(e.target.value)} 
                />
              </div>
            )}

            <div className="modal-actions mt-2">
              <button className="btn btn-secondary" onClick={() => setIsScheduling(false)}>{t("common.cancel", "Cancel")}</button>
              <button className="btn" onClick={saveSchedule} disabled={!selectedRoutineId}>{t("common.save", "Save")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
