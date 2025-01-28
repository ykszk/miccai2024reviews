# %% metadata for Pretty Jupyter [raw]
# title: MICCAI 2024 Paper Analysis

#%%
import pandas as pd
import seaborn as sns
from IPython.display import display, HTML
from pathlib import Path

def tag(tag, content):
    t = f"<{tag}>{content}</{tag}>"
    display(HTML(t))

def h2(line):
    tag("h2", line)

sns.set_theme(context='notebook', style='whitegrid', font='serif', rc={'figure.figsize':(8, 6), 'figure.dpi': 100})

html = '''<p>Analysis based on data collected from MICCAI 2024 <a href="https://papers.miccai.org/miccai-2024/">open access web site</a>.</p>
<p>source code: <a href="https://github.com/ykszk/miccai2024reviews">🐙🐈</a></p>
'''
display(HTML(html))

if '__file__' in locals():
    data_dir = Path(__file__).parent.parent / "data"
else:
    data_dir = Path("data")
df = pd.read_csv(data_dir / "papers.csv")
df.set_index("id", inplace=True)
#%%
h2("Paper Categories")
categories = pd.DataFrame(df['category'].value_counts())
display(HTML(categories.T.to_html()) )

#%%
categories_count_above_20 = categories[df['category'].value_counts() > 20]
df['category_id'] = df['category'].astype('category').cat.codes.astype(str)
# %%
h2("Review Score Distribution")
review_score_cols = [c for c in df.columns if "review_score" in c]
df['mean_review_score'] = df[review_score_cols].mean(axis=1)
ax = sns.histplot(data=df, x='mean_review_score', element="step")

# %%
h2("Review Score of Early Accept Papers")
rebuttal_score_cols = [c for c in df.columns if "post_rebuttal_score" in c]
df['mean_rebuttal_score'] = df[rebuttal_score_cols].mean(axis=1)
df['early_accept'] = df['mean_rebuttal_score'].isna()
ax = sns.histplot(data=df, x='mean_review_score', hue='early_accept', element="step")


# %%
h2("Review Score Distribution by Category")
df_category_above_20 = df[df['category'].isin(categories_count_above_20.index)]
ax = sns.histplot(data=df_category_above_20, x='mean_review_score', element="step", multiple='stack', hue='category')
sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))

# %%
h2("Post-Rebuttal Review Score Distribution")
# df['mean_rebuttal_score'].hist()
ax = sns.histplot(data=df, x='mean_rebuttal_score', element="step")

#%%
h2("Review Score vs Post-Rebuttal Review Score")
df_late = df.dropna(subset=['mean_rebuttal_score'])

ax = sns.jointplot(data=df_late, x='mean_review_score', y='mean_rebuttal_score', kind='reg')

# %%
h2("Papers with the best review score")
top_review_scores = df.sort_values('mean_review_score', ascending=False)
cols = ['title', 'url', 'authors', 'category', 'mean_review_score', 'mean_rebuttal_score']
best_score = df['mean_review_score'].max()
df_top = top_review_scores[cols][top_review_scores['mean_review_score'] == best_score]
df_top.set_index('title', inplace=True)
df_top['url'] = df_top['url'].apply(lambda x: f'<a href="{x}" target="_blank">link</a>')
display(HTML(df_top.to_html(escape=False)))

#%%
h2("Papers with the best post-rebuttal review score")
top_rebuttal_scores = df.sort_values('mean_rebuttal_score', ascending=False)
best_rebuttal_score = df['mean_rebuttal_score'].max()
df_top_rebuttal = top_rebuttal_scores[cols][top_rebuttal_scores['mean_rebuttal_score'] == best_rebuttal_score]
df_top_rebuttal.set_index('title', inplace=True)
df_top_rebuttal['url'] = df_top_rebuttal['url'].apply(lambda x: f'<a href="{x}" target="_blank">link</a>')
display(HTML(df_top_rebuttal.to_html(escape=False)))



