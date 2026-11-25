import oracledb


def check_connection(
    host: str,
    port: int,
    service: str,
    user: str,
    password: str,
) -> dict:

    dsn = f"{host}:{port}/{service}"

    try:
        with oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
            tcp_connect_timeout=5,
        ) as connection:

            with connection.cursor() as cursor:
                cursor.execute("SELECT USER FROM dual")
                row = cursor.fetchone()

            return {
                "success": True,
                "db_version": connection.version,
                "session_user": row[0],
            }

    except oracledb.Error as exc:
        error_code = None
        error_message = str(exc)

        if exc.args:
            error_code = getattr(exc.args[0], "code", None)

        if (
            error_code == 1017
            or "ORA-01017" in error_message
        ):
            error_type = "authentication"

        elif (
            error_code in (12514, 12505)
            or "DPY-6001" in error_message
            or "ORA-12514" in error_message
            or "ORA-12505" in error_message
        ):
            error_type = "service_not_found"

        elif (
            error_code == 12516
            or "ORA-12516" in error_message
        ):
            error_type = "service_unavailable"

        elif (
            error_code in (
                12170,
                12541,
                12543,
                12545,
                12535,
                12537,
                12547,
            )
            or "DPY-6005" in error_message
        ):
            error_type = "database_unavailable"

        else:
            error_type = "connection_error"

        return {
            "success": False,
            "error_type": error_type,
        }

    except (OSError, ValueError):
        return {
            "success": False,
            "error_type": "database_unavailable",
        }


test_connection = check_connection