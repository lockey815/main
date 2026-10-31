import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { settingsApi } from "../services/api.js";
import { useAuth } from "./AuthContext.jsx";

const Ctx = createContext(null);
export const useFacility = () => useContext(Ctx);

const FALLBACK = { facility_name: "LeukNet", address: "", contact: "", email: "", logo_data_url: "", report_footer: "" };

export function SettingsProvider({ children }) {
  const { isAuthed } = useAuth();
  const [settings, setSettings] = useState(FALLBACK);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setSettings(await settingsApi.get());
    } catch {
      /* backend may be waking up - keep fallback */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (isAuthed) refresh();
    else {
      setSettings(FALLBACK);
      setLoaded(false);
    }
  }, [isAuthed, refresh]);

  return <Ctx.Provider value={{ settings, setSettings, refresh, loaded }}>{children}</Ctx.Provider>;
}
