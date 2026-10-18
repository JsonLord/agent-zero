# v5.1 build fix

The v5 build reached the final Supervisor validation step and failed because the
Dockerfile used a regular-expression grep for the literal include path:

    /a0/usr/supervisor/*.conf

The Supervisor config itself was copied successfully.

v5.1 replaces the regex check with fixed-string grep:

    grep -Fq '/a0/usr/supervisor/*.conf' /etc/supervisor/conf.d/supervisord.conf

No runtime behavior or package versions changed.
