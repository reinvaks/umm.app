from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from umm_client import fetch_umm_messages

st.set_page_config(page_title='Nord Pool UMM Lab', page_icon='📣', layout='wide')
st.title('📣 Nord Pool UMM Lab')
st.caption('Isoleeritud testirakendus Nord Pool UMM REST API värskuse, versioonide ja payload’i kontrollimiseks. BalticPulse ei sõltu sellest rakendusest.')

@st.cache_data(ttl=20)
def load():
    return fetch_umm_messages(limit=500,max_pages=2,retries=2)

rows, meta = load()
if meta.error:
    st.error(f'API error: {meta.error}')
else:
    df=pd.DataFrame(rows)
    st.metric('HTTP', meta.status_code or 200)
    st.metric('Teateid', len(df))
    if not df.empty:
        df['publication_time']=pd.to_datetime(df['publication_time'],utc=True,errors='coerce')
        df=df.sort_values('publication_time',ascending=False,na_position='last')
        newest=df['publication_time'].dropna().max()
        if pd.notna(newest):
            age=(pd.Timestamp.now(tz='UTC')-newest).total_seconds()/60
            st.metric('Uusim publicationDate', newest.strftime('%Y-%m-%d %H:%M UTC'), delta=f'{age:.0f} min tagasi', delta_color='off')
        cols=[c for c in ['publication_time','message_id','version','area','asset_name','market_participant','status','message_type','affected_capacity','event_start','event_end','is_outdated','source_url'] if c in df.columns]
        st.dataframe(df[cols],hide_index=True,use_container_width=True,column_config={'source_url':st.column_config.LinkColumn('Nord Pool')})
        st.markdown('### Viimase API rea raw payload')
        raw=df.iloc[0].get('raw')
        st.json(raw if isinstance(raw,dict) else {})

if st.button('Värskenda nüüd'):
    st.cache_data.clear(); st.rerun()

st.info('SignalR production hub: https://ummwsng.nordpoolgroup.com/messageHub. Push-integratsiooni ei lisata enne, kui hub-event ja payload contract on Nord Pool Developer Portali järgi kontrollitud.')
