SELECT B.RESPONSIBILITY_NAME
FROM FND_USER_RESP_GROUPS A,
FND_RESPONSIBILITY_VL B, 
FND_USER C
WHERE A.responsibility_id = B.responsibility_id AND
C.user_id = A.user_id AND
(to_char(A.end_date) IS NULL
OR A.end_date > sysdate)
AND C.user_name = '&user';
