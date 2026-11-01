
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi, tokenStore } from "../services/api.js";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(tokenStore.get());
  const [email, setEmail] = useState(localStorage.getItem("leuknet_email") || "");

  const saveSession = useCallback((data) => {
    tokenStore.set(data.access_token);
    localStorage.setItem("leuknet_email", data.email);
    setToken(data.access_token);
    setEmail(data.email);
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    localStorage.removeItem("leuknet_email");
    setToken(null);
    setEmail("");
  }, []);

  useEffect(() => {
    window.addEventListener("leuknet:logout", logout);
    return () => window.removeEventListener("leuknet:logout", logout);
  }, [logout]);

  const login = useCallback(async (mail, password) => {
    const data = await authApi.login(mail, password);
    saveSession(data);
  }, [saveSession]);

  const register = useCallback(async (mail, password) => {
    const data = await authApi.register(mail, password);
    saveSession(data);
  }, [saveSession]);

  return (
    <Ctx.Provider value={{
      token,
      email,
      isAuthed: !!token,
      login,
      register,
      logout
    }}>
      {children}
    </Ctx.Provider>
  );
}
