FROM python:3.7.3

COPY Server.py /Server.py

RUN pip install numpy
RUN pip install pandas

CMD python /Server.py --client_dir /client/ --log_dir /log/ --house_target_fn /house_target_tuple.json --existing_games_fn /all.json