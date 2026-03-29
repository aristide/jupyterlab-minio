# jupyterlab-minio: load MinIO env vars from shared JSON file.
# This script is automatically installed by jupyterlab-minio into
# ~/.julia/config/startup.jl and runs each time a Julia session starts.

let
    env_file = joinpath(homedir(), ".jupyter", "minio_env.json")
    if isfile(env_file)
        try
            raw = read(env_file, String)
            # Use stdlib JSON parsing if available, otherwise regex fallback
            data = try
                import JSON
                JSON.parse(raw)
            catch
                # Minimal regex-based parsing for simple flat JSON
                d = Dict{String,String}()
                for m in eachmatch(r"\"([^\"]+)\"\s*:\s*\"([^\"]*)\"", raw)
                    d[m.captures[1]] = m.captures[2]
                end
                d
            end
            for k in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")
                v = get(data, k, "")
                if !isempty(v)
                    ENV[k] = v
                else
                    delete!(ENV, k)
                end
            end
        catch
            # Silently ignore parse errors
        end
    end
end
