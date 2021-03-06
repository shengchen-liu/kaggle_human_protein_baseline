from common import *
from sklearn.model_selection import KFold, StratifiedKFold

all_files = pd.read_csv("./input/train.csv")


# oversample
s = Oversampling("./input/train.csv")
sample_names = all_files['Id']
sample_names = [idx for idx in sample_names for _ in range(s.get(idx))]
all_files = all_files.copy().set_index('Id')
all_files = all_files.reindex(sample_names)
all_files = all_files.rename_axis('Id').reset_index()

all_names = np.array(all_files['Id'])
all_targets = np.array(all_files['Target'])

# skf = KFold(n_splits=5, shuffle=True)
skf = StratifiedKFold(n_splits=5, shuffle=True)
skf.get_n_splits(all_files, all_targets)

for f, (train_index, test_index) in enumerate(skf.split(all_files, all_targets)):
   print("TRAIN:", len(train_index), "TEST:", len(test_index))
   X_train, X_test= all_names[train_index], all_names[test_index]
   y_train, y_test = all_targets[train_index], all_targets[test_index]

   # with open(os.path.join("input/fold_5", "train_fol5_{}.txt".format(f)),"w+") as text_file:
   #     text_file.write(X_train)
   np.savetxt(os.path.join("input/fold_5", "train_fold5_{}.txt".format(f)), X_train,fmt='%s')
   np.savetxt(os.path.join("input/fold_5", "test_fold5_{}.txt".format(f)), X_test,fmt='%s')


print(skf)