[~,batch_points,~,~,batch_index] = kmedoids(candidates,16);

% [c1,c2,c3]=unique(candidates,'rows');
% 
% repeats=[]; %%% tells the number of repeated designs in c1
% best_repeated=[];
% best_repeated_imp=[];
% high_repeated=[];
% best_repeated_ind=[];
% 
% for i = 1 : size(c1,1)
%     ind=find(ismember(candidates,c1(i,:),'rows'));
%     repeats(i,1)=size(ind,1);
%     imp=improvements(ind);
%     [~,bb]=max(imp);
%     best_repeated(i,:)=candidates(ind(bb),:);
%     best_repeated_imp(i,1)=improvements(ind(bb),:);
%     best_repeated_ind(i,:)=ind(bb);
% end
% 
% [repeats_sorted,bb]=sort(repeats,'descend');
% high_repeated=c1(bb,:);
% 
% [bests_sorted,bb]=sort(best_repeated_imp,'descend');
% best_repeated_sorted=c1(bb,:);


int_ind=[];
int_avg=[];
int_max=[];

for x = 1 : 16
    ind=find(ismember(candidates,batch_points(x,:),'rows'));
    int_ind(x,1)=size(ind,1);
int_avg(x,1)=mean(improvements(ind));
int_max(x,1)=max(improvements(ind));

end